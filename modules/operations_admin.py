"""Minimal operational administration using canonical auth IDs and audit snapshots."""
import json

from database.db_connection import fetch_all, using_postgres
from database.transactions import transaction, one
from modules.domain_errors import DomainError
from modules.order_workflow import live_actor, require_role
from modules.order_service import money


def overview(user):
    require_role(user, {"ADMIN"})
    return {
        "users": fetch_all("SELECT id_auth_user,nombre,correo,rol,estado FROM auth_users ORDER BY id_auth_user"),
        "restaurants": fetch_all("SELECT * FROM restaurantes ORDER BY id_restaurante"),
        "operators": fetch_all("SELECT * FROM comercio_operadores"),
        "couriers": fetch_all("""SELECT u.id_auth_user,u.nombre,u.estado,c.disponible,
            (SELECT COUNT(*) FROM pedido_asignaciones a JOIN pedidos p ON p.id_pedido=a.id_pedido
             WHERE a.id_courier=u.id_auth_user AND p.estado NOT IN ('DELIVERED','CANCELLED')) AS active_deliveries
            FROM auth_users u LEFT JOIN courier_profiles c ON c.id_auth_user=u.id_auth_user WHERE u.rol='COURIER'"""),
        "audit": fetch_all("SELECT * FROM operaciones_auditoria ORDER BY fecha DESC LIMIT 100"),
    }


def audit(conn, user, request_id, action, resource, detail):
    serialized = json.dumps(detail, sort_keys=True, ensure_ascii=False)
    old = one(conn, "SELECT * FROM operaciones_auditoria WHERE request_id=?", (request_id,))
    if old:
        if old["actor_id"] != user["id_auth_user"] or old["accion"] != action or old["recurso_id"] != resource or old["detalle"] != serialized:
            raise DomainError("Clave de solicitud reutilizada con contenido diferente")
        return False
    conn.execute("""INSERT INTO operaciones_auditoria(request_id,actor_id,actor_nombre,actor_rol,accion,recurso_id,detalle)
        VALUES (?,?,?,?,?,?,?)""", (request_id, user["id_auth_user"], user["nombre"], user["rol"], action, resource, serialized))
    return True


def update_user(admin, user_id, role, active, request_id, reason):
    require_role(admin, {"ADMIN"})
    with transaction() as conn:
        # One administrative writer prevents last-admin races and inconsistent role/grant changes.
        if using_postgres():
            conn.execute("SELECT pg_advisory_xact_lock(20261107)")
        admin = live_actor(conn, admin)
        target = one(conn, "SELECT * FROM auth_users WHERE id_auth_user=?", (user_id,))
        if not target:
            raise DomainError("Usuario no encontrado", 404)
        if not audit(conn, admin, request_id, "USER", user_id, [role, active, reason]):
            return
        if target["rol"] == "ADMIN" and (role != "ADMIN" or not active):
            count = one(conn, "SELECT COUNT(*) AS n FROM auth_users WHERE rol='ADMIN' AND estado='ACTIVO'")["n"]
            if count <= 1:
                raise DomainError("Debe conservarse un administrador activo")
        busy = one(conn, """SELECT 1 FROM pedido_asignaciones a JOIN pedidos p ON p.id_pedido=a.id_pedido
            WHERE a.id_courier=? AND p.estado NOT IN ('DELIVERED','CANCELLED')""", (user_id,))
        if busy and (role != "COURIER" or not active):
            raise DomainError("Reasigna la entrega activa antes de cambiar este usuario")
        conn.execute("UPDATE auth_users SET rol=?,estado=? WHERE id_auth_user=?", (role, "ACTIVO" if active else "INACTIVO", user_id))
        if role != "MERCHANT" or not active:
            conn.execute("UPDATE comercio_operadores SET activo=0 WHERE id_auth_user=?", (user_id,))
        if role != "COURIER" or not active:
            conn.execute("UPDATE courier_profiles SET disponible=0 WHERE id_auth_user=?", (user_id,))
        if role == "COURIER":
            conn.execute("INSERT INTO courier_profiles(id_auth_user) VALUES (?) ON CONFLICT (id_auth_user) DO NOTHING", (user_id,))


def grant(admin, restaurant_id, user_id, active, edit_products, request_id, reason):
    require_role(admin, {"ADMIN"})
    with transaction() as conn:
        if using_postgres():
            conn.execute("SELECT pg_advisory_xact_lock(20261107)")
        admin = live_actor(conn, admin)
        target = one(conn, "SELECT rol,estado FROM auth_users WHERE id_auth_user=?", (user_id,))
        restaurant = one(conn, "SELECT 1 FROM restaurantes WHERE id_restaurante=?", (restaurant_id,))
        if not restaurant or not target:
            raise DomainError("Establecimiento o usuario inexistente", 404)
        if active and (target["rol"] != "MERCHANT" or target["estado"] != "ACTIVO"):
            raise DomainError("El operador debe ser MERCHANT activo")
        if not audit(conn, admin, request_id, "GRANT", restaurant_id, [user_id, active, edit_products, reason]):
            return
        conn.execute("""INSERT INTO comercio_operadores(id_restaurante,id_auth_user,activo,puede_editar_productos)
            VALUES (?,?,?,?) ON CONFLICT (id_restaurante,id_auth_user) DO UPDATE
            SET activo=excluded.activo,puede_editar_productos=excluded.puede_editar_productos""",
            (restaurant_id, user_id, int(active), int(edit_products)))


def availability(user, available, request_id):
    require_role(user, {"COURIER"})
    with transaction() as conn:
        user = live_actor(conn, user)
        if audit(conn, user, request_id, "AVAILABILITY", user["id_auth_user"], [available]):
            conn.execute("""INSERT INTO courier_profiles(id_auth_user,disponible) VALUES (?,?)
                ON CONFLICT (id_auth_user) DO UPDATE SET disponible=excluded.disponible""", (user["id_auth_user"], int(available)))


def products(user):
    require_role(user, {"MERCHANT", "ADMIN"})
    if user["rol"] == "ADMIN":
        return fetch_all("SELECT p.*,r.nombre AS restaurante,1 AS puede_editar_productos FROM productos p JOIN restaurantes r ON r.id_restaurante=p.id_restaurante")
    return fetch_all("""SELECT p.*,r.nombre AS restaurante,o.puede_editar_productos FROM productos p
        JOIN restaurantes r ON r.id_restaurante=p.id_restaurante JOIN comercio_operadores o ON o.id_restaurante=p.id_restaurante
        WHERE o.id_auth_user=? AND o.activo=1""", (user["id_auth_user"],))


def update_product(user, product_id, name, price, available, request_id):
    require_role(user, {"ADMIN", "MERCHANT"})
    with transaction() as conn:
        user = live_actor(conn, user)
        product = one(conn, "SELECT * FROM productos WHERE id_producto=?", (product_id,))
        if not product:
            raise DomainError("Producto no encontrado", 404)
        if user["rol"] == "MERCHANT":
            allowed = one(conn, """SELECT 1 FROM comercio_operadores WHERE id_auth_user=? AND id_restaurante=?
                AND activo=1 AND puede_editar_productos=1""", (user["id_auth_user"], product["id_restaurante"]))
            if not allowed:
                raise DomainError("No tienes autorización para editar este producto", 403)
        price = float(money(price))
        if audit(conn, user, request_id, "PRODUCT", product_id, [name, price, available]):
            conn.execute("UPDATE productos SET nombre=?,precio=?,disponible=? WHERE id_producto=?", (name, price, int(available), product_id))


def update_restaurant(admin, restaurant_id, address, responsible, active, request_id):
    require_role(admin, {"ADMIN"})
    with transaction() as conn:
        admin = live_actor(conn, admin)
        if not one(conn, "SELECT 1 FROM restaurantes WHERE id_restaurante=?", (restaurant_id,)):
            raise DomainError("Establecimiento no encontrado", 404)
        if audit(conn, admin, request_id, "RESTAURANT", restaurant_id, [address, responsible, active]):
            conn.execute("UPDATE restaurantes SET direccion=?,responsable=?,activo=? WHERE id_restaurante=?",
                         (address, responsible, int(active), restaurant_id))
