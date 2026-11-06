"""Order authorization and transitions. Every write shares the same transaction/lock."""
import json

from database.db_connection import fetch_all, using_postgres
from database.transactions import transaction, one
from modules.domain_errors import DomainError

STATES = {"RECEIVED", "ACCEPTED", "PREPARING", "READY_FOR_PICKUP", "IN_TRANSIT", "DELIVERED", "CANCELLED"}
NEXT = {"RECEIVED": "ACCEPTED", "ACCEPTED": "PREPARING", "PREPARING": "READY_FOR_PICKUP",
        "READY_FOR_PICKUP": "IN_TRANSIT", "IN_TRANSIT": "DELIVERED"}


def require_role(user, roles):
    if user["rol"] not in roles:
        raise DomainError("No tienes permisos para esta operación", 403)


def live_actor(conn, user):
    if using_postgres():
        conn.execute("SELECT pg_advisory_xact_lock(20261107)")
    query = "SELECT * FROM auth_users WHERE id_auth_user=? AND estado='ACTIVO'"
    if using_postgres():
        query += " FOR SHARE"
    actor = one(conn, query, (user["id_auth_user"],))
    if not actor or actor["rol"] != user["rol"]:
        raise DomainError("La sesión cambió. Inicia sesión nuevamente", 401)
    return actor


def lock_order(conn, order_id):
    query = "SELECT * FROM pedidos WHERE id_pedido=?"
    if using_postgres():
        query += " FOR UPDATE"
    row = one(conn, query, (order_id,))
    if not row:
        raise DomainError("Pedido no encontrado", 404)
    return row


def authorize_order(conn, order, user):
    role = user["rol"]
    if role == "ADMIN":
        return
    if role == "CLIENT":
        owner = one(conn, "SELECT correo FROM clientes WHERE id_cliente=?", (order["id_cliente"],))
        if owner and owner["correo"].lower() == user["correo"].lower():
            return
    if role == "MERCHANT" and one(conn, """SELECT 1 FROM comercio_operadores
        WHERE id_restaurante=? AND id_auth_user=? AND activo=1""", (order["id_restaurante"], user["id_auth_user"])):
        return
    if role == "COURIER" and one(conn, "SELECT 1 FROM pedido_asignaciones WHERE id_pedido=? AND id_courier=?",
                                 (order["id_pedido"], user["id_auth_user"])):
        return
    if role == "AGENT" and one(conn, "SELECT 1 FROM reclamos WHERE id_pedido=?", (order["id_pedido"],)):
        return
    raise DomainError("No tienes acceso a este pedido", 403)


def visible_order_ids(user):
    base = "SELECT p.id_pedido FROM pedidos p "
    role, uid = user["rol"], user["id_auth_user"]
    if role == "ADMIN":
        query, params = base, ()
    elif role == "CLIENT":
        query, params = base + "JOIN clientes c ON c.id_cliente=p.id_cliente WHERE lower(c.correo)=lower(?)", (user["correo"],)
    elif role == "MERCHANT":
        query, params = base + "WHERE EXISTS (SELECT 1 FROM comercio_operadores o WHERE o.id_restaurante=p.id_restaurante AND o.id_auth_user=? AND o.activo=1)", (uid,)
    elif role == "COURIER":
        query, params = base + "JOIN pedido_asignaciones a ON a.id_pedido=p.id_pedido WHERE a.id_courier=?", (uid,)
    else:
        require_role(user, {"AGENT"})
        query, params = base + "WHERE EXISTS (SELECT 1 FROM reclamos r WHERE r.id_pedido=p.id_pedido)", ()
    return fetch_all(query + " ORDER BY p.id_pedido DESC", params)


def events(order_id, internal=False):
    rows = fetch_all("SELECT * FROM pedido_eventos WHERE id_pedido=? ORDER BY version_operativa", (order_id,))
    if internal:
        return rows
    return [{key: row[key] for key in ("accion", "estado_anterior", "estado_nuevo", "fecha")} for row in rows]


def _retry(conn, order, user, request_id, payload):
    previous = one(conn, "SELECT * FROM pedido_eventos WHERE request_id=?", (request_id,))
    if not previous:
        return False
    if (previous["id_pedido"] != order["id_pedido"] or previous["actor_id"] != user["id_auth_user"]
            or previous["payload_json"] != payload):
        raise DomainError("La clave de solicitud ya identifica otra operación")
    return True


def record(conn, order, user, request_id, action, state, reason=None, courier=None, payload="{}"):
    conn.execute("""INSERT INTO pedido_eventos
        (request_id,id_pedido,actor_id,actor_nombre,actor_rol,accion,estado_anterior,estado_nuevo,motivo,courier_id,payload_json,version_operativa)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", (request_id, order["id_pedido"], user["id_auth_user"], user["nombre"],
            user["rol"], action, order["estado"], state, reason, courier, payload, order.get("version_operativa", -1) + 1))
    customer = one(conn, """SELECT c.correo,p.codigo_pedido FROM pedidos p
        JOIN clientes c ON c.id_cliente=p.id_cliente WHERE p.id_pedido=?""", (order["id_pedido"],))
    from modules.notification_service import emit
    recipients = {customer["correo"]}
    for row in conn.execute("""SELECT u.correo FROM pedidos p JOIN comercio_operadores o ON o.id_restaurante=p.id_restaurante
        JOIN auth_users u ON u.id_auth_user=o.id_auth_user WHERE p.id_pedido=? AND o.activo=1 AND u.estado='ACTIVO' AND u.rol='MERCHANT'""", (order["id_pedido"],)):
        recipients.add(row["correo"])
    for row in conn.execute("""SELECT u.correo FROM pedido_asignaciones a JOIN auth_users u ON u.id_auth_user=a.id_courier
        WHERE a.id_pedido=? AND u.estado='ACTIVO' AND u.rol='COURIER'""", (order["id_pedido"],)):
        recipients.add(row["correo"])
    for email in recipients:
        emit(conn, email, "ORDER_" + action, order["id_pedido"], request_id, "Actualización de pedido",
             f"Pedido {customer['codigo_pedido']}. Evento registrado: {action}. Estado: {state}.", order=True)


def transition(order_id, user, state, expected_version, request_id, reason=None):
    require_role(user, {"MERCHANT", "COURIER", "ADMIN"})
    if state not in STATES:
        raise DomainError("Estado operativo no válido", 422)
    reason = (reason or "").strip() or None
    payload = json.dumps(["transition", state, expected_version, reason])
    with transaction() as conn:
        user = live_actor(conn, user)
        order = lock_order(conn, order_id)
        authorize_order(conn, order, user)
        if _retry(conn, order, user, request_id, payload):
            return
        current = order["estado"]
        if order["version_operativa"] != expected_version:
            raise DomainError("El pedido cambió. Recarga antes de operar")
        if current in {"DELIVERED", "CANCELLED"}:
            raise DomainError("El pedido está en un estado final")
        if user["rol"] == "ADMIN":
            if not reason:
                raise DomainError("La intervención administrativa exige motivo", 422)
            # Exceptional correction of legacy DELAYED never infers its physical phase.
            valid = (current == "DELAYED" and state in {"PREPARING", "READY_FOR_PICKUP", "CANCELLED"}
                     or NEXT.get(current) == state or state == "CANCELLED")
        elif user["rol"] == "MERCHANT":
            valid = (current in {"RECEIVED", "ACCEPTED", "PREPARING"} and NEXT.get(current) == state
                     or current == "RECEIVED" and state == "CANCELLED" and bool(reason))
        else:
            valid = (current in {"READY_FOR_PICKUP", "IN_TRANSIT"} and NEXT.get(current) == state)
        if not valid:
            raise DomainError("Transición no permitida para este rol y estado")
        if state in {"IN_TRANSIT", "DELIVERED"}:
            assigned = one(conn, """SELECT a.*,u.estado,u.rol FROM pedido_asignaciones a
                JOIN auth_users u ON u.id_auth_user=a.id_courier WHERE a.id_pedido=?""", (order_id,))
            if not assigned or assigned["estado"] != "ACTIVO" or assigned["rol"] != "COURIER":
                raise DomainError("Se requiere un repartidor activo asignado")
            if state == "DELIVERED" and not order["recogido_at"]:
                raise DomainError("No consta la recogida del pedido")
        updates = "estado=?, version_operativa=version_operativa+1"
        if state == "IN_TRANSIT":
            updates += ", recogido_at=CURRENT_TIMESTAMP"
        if state == "DELIVERED":
            updates += ", entregado_at=CURRENT_TIMESTAMP"
        conn.execute(f"UPDATE pedidos SET {updates} WHERE id_pedido=?", (state, order_id))
        record(conn, order, user, request_id, "TRANSITION", state, reason, payload=payload)


def assign(order_id, user, courier_id, expected_version, request_id, reason):
    require_role(user, {"ADMIN"})
    payload = json.dumps(["assign", courier_id, expected_version, reason.strip()])
    with transaction() as conn:
        user = live_actor(conn, user)
        order = lock_order(conn, order_id)
        if _retry(conn, order, user, request_id, payload):
            return
        if order["estado"] != "READY_FOR_PICKUP" or order["version_operativa"] != expected_version:
            raise DomainError("El pedido debe estar listo y en la versión esperada")
        query = "SELECT * FROM auth_users WHERE id_auth_user=?"
        if using_postgres():
            query += " FOR UPDATE"
        courier = one(conn, query, (courier_id,))
        profile = one(conn, "SELECT * FROM courier_profiles WHERE id_auth_user=?", (courier_id,))
        if not courier or courier["estado"] != "ACTIVO" or courier["rol"] != "COURIER" or not profile or not profile["disponible"]:
            raise DomainError("Repartidor inactivo o no disponible")
        busy = one(conn, """SELECT 1 FROM pedido_asignaciones a JOIN pedidos p ON p.id_pedido=a.id_pedido
            WHERE a.id_courier=? AND p.estado NOT IN ('DELIVERED','CANCELLED')""", (courier_id,))
        if busy:
            raise DomainError("El repartidor ya tiene una entrega activa")
        conn.execute("""INSERT INTO pedido_asignaciones(id_pedido,id_courier) VALUES (?,?)
            ON CONFLICT (id_pedido) DO UPDATE SET id_courier=excluded.id_courier,asignado_at=CURRENT_TIMESTAMP""", (order_id, courier_id))
        conn.execute("UPDATE pedidos SET version_operativa=version_operativa+1,repartidor=? WHERE id_pedido=?", (courier["nombre"], order_id))
        record(conn, order, user, request_id, "ASSIGN", order["estado"], reason.strip(), courier_id, payload)


def record_created(conn, order_id, user, request_id, payload):
    record(conn, {"id_pedido": order_id, "estado": None}, user, request_id, "CREATED", "RECEIVED", payload=payload)


def report_delay(order_id, user, expected_version, request_id, reason):
    require_role(user, {"ADMIN", "MERCHANT"})
    payload = json.dumps(["delay", expected_version, reason])
    with transaction() as conn:
        user = live_actor(conn, user)
        order = lock_order(conn, order_id)
        authorize_order(conn, order, user)
        if _retry(conn, order, user, request_id, payload):
            return
        if order["version_operativa"] != expected_version or order["estado"] in {"DELIVERED", "CANCELLED"}:
            raise DomainError("No puede registrarse demora sobre esta versión o estado final")
        conn.execute("UPDATE pedidos SET version_operativa=version_operativa+1 WHERE id_pedido=?", (order_id,))
        record(conn, order, user, request_id, "DELAY_REPORTED", order["estado"], reason, payload=payload)
