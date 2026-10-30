"""Catalog-authorized prices and immutable order snapshots, without payment processing."""
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
import json
from uuid import uuid4

from database.db_connection import using_postgres
from database.transactions import transaction, one, insert
from modules.domain_errors import DomainError

SERVICE_FEE = Decimal("2.00")  # Existing checkout service charge; now calculated only here.


def money(value):
    try:
        result = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise DomainError("Importe de catálogo no válido", 422) from exc
    if not result.is_finite() or result < 0:
        raise DomainError("Importe de catálogo no válido", 422)
    return result


def _quote(conn, requested):
    quantities = {}
    for item in requested:
        product_id, quantity = item["product_id"], item["quantity"]
        quantities[product_id] = quantities.get(product_id, 0) + quantity
        if quantities[product_id] > 2147483647:
            raise DomainError("Cantidad fuera del rango admitido", 422)
    lines, deliveries = [], {}
    for product_id, quantity in sorted(quantities.items()):
        query = """SELECT p.*,r.nombre AS restaurante,r.imagen AS imagen_restaurante,
                   r.costo_delivery,r.activo FROM productos p JOIN restaurantes r
                   ON r.id_restaurante=p.id_restaurante WHERE p.id_producto=?"""
        if using_postgres():
            query += " FOR SHARE OF p,r"
        product = one(conn, query, (product_id,))
        if not product or not product["activo"] or not product["disponible"]:
            raise DomainError("Producto o establecimiento no disponible", 422)
        price = money(product["precio"])
        deliveries[product["id_restaurante"]] = money(product["costo_delivery"])
        lines.append(dict(productId=product_id, restaurantId=product["id_restaurante"],
                          restaurantName=product["restaurante"], restaurantImage=product["imagen_restaurante"],
                          name=product["nombre"], image=product["imagen"], price=float(price), quantity=quantity))
    subtotal = sum((money(line["price"]) * line["quantity"] for line in lines), Decimal("0.00"))
    confirmable = len(deliveries) == 1
    delivery = next(iter(deliveries.values())) if confirmable else None
    fingerprint = json.dumps({"lines": lines, "delivery": {str(k): str(v) for k, v in deliveries.items()},
                              "service": str(SERVICE_FEE)}, sort_keys=True, separators=(",", ":"))
    return dict(items=lines, subtotal=float(subtotal), delivery=float(delivery) if delivery is not None else None,
                service=float(SERVICE_FEE) if confirmable else None,
                total=float(subtotal + delivery + SERVICE_FEE) if confirmable else None,
                canConfirm=confirmable, quoteHash=hashlib.sha256(fingerprint.encode()).hexdigest(),
                limitation=None if confirmable else "La confirmación con varios establecimientos requiere una política de cargos y pedidos aún no definida.")


def quote_order(items):
    with transaction() as conn:
        return _quote(conn, items)


def create_catalog_order(user, items, quote_hash, payment_method, address, notes=None):
    with transaction() as conn:
        quote = _quote(conn, items)
        if not quote["canConfirm"]:
            raise DomainError(quote["limitation"])
        if quote_hash != quote["quoteHash"]:
            raise DomainError("El catálogo cambió. Revisa la nueva cotización antes de confirmar.")
        customer = one(conn, "SELECT id_cliente FROM clientes WHERE lower(correo)=lower(?) ORDER BY id_cliente LIMIT 1", (user["correo"],))
        customer_id = customer["id_cliente"] if customer else insert(conn,
            "INSERT INTO clientes(nombre,correo,telefono) VALUES (?,?,?)", (user["nombre"], user["correo"], user.get("telefono")))
        first = quote["items"][0]
        order_id = insert(conn, """INSERT INTO pedidos
            (codigo_pedido,id_cliente,id_restaurante,tienda_nombre,tienda_imagen,estado,total,metodo_pago,
             direccion_entrega,notas_entrega,subtotal,costo_delivery,costo_servicio,fecha_entrega_estimada)
            VALUES (?,?,?,?,?,'PREPARING',?,?,?,?,?,?,?,?)""", (
                "ORD-" + datetime.now().strftime("%Y%m%d") + "-" + uuid4().hex[:12].upper(), customer_id,
                first["restaurantId"], first["restaurantName"], first["restaurantImage"], quote["total"],
                payment_method, address, notes, quote["subtotal"], quote["delivery"], quote["service"],
                (datetime.now() + timedelta(minutes=35)).isoformat(timespec="seconds")))
        for line in quote["items"]:
            insert(conn, """INSERT INTO pedido_items(id_pedido,id_producto,nombre_producto,cantidad,precio,imagen)
                           VALUES (?,?,?,?,?,?)""", (order_id,line["productId"],line["name"],line["quantity"],line["price"],line["image"]))
        return order_id
