"""Persistent, transactional notifications and recipient-scoped read tracking."""
from database.db_connection import fetch_all
from database.transactions import insert, one, transaction
from modules.domain_errors import DomainError


def emit(conn, email, event, resource_id, key, title, message, *, order=False, inserter=None):
    email = email.strip().lower()
    account = one(conn, "SELECT id_auth_user,estado FROM auth_users WHERE lower(correo)=?", (email,))
    notification_key = f"{event}:{key}:{email}"
    (inserter or insert)(conn, """INSERT INTO notificaciones
        (correo_cliente,id_destinatario,id_reclamo,id_pedido,evento,clave_evento,titulo,mensaje,tipo)
        VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT (clave_evento) DO NOTHING""",
        (email, account["id_auth_user"] if account else None, None if order else resource_id,
         resource_id if order else None, event, notification_key, title, message,
         "INFO" if order else "RESPUESTA" if event in {"CLAIM_PUBLISHED", "AGENT_MESSAGE"} else "ALERTA"))


def claim_audience(conn, claim):
    responsible = one(conn, "SELECT correo FROM auth_users WHERE id_auth_user=? AND estado='ACTIVO' AND rol IN ('AGENT','ADMIN')",
                      (claim.get("responsable_auth_id"),))
    if responsible:
        return [responsible["correo"]]
    return [row["correo"] for row in conn.execute("SELECT correo FROM auth_users WHERE estado='ACTIVO' AND rol IN ('AGENT','ADMIN')")]


def claim_event(conn, claim, event, key, *, client=False, staff=False):
    recipients = set(claim_audience(conn, claim) if staff else [])
    if client:
        recipients.add(claim["correo_cliente"])
    titles = {
        "CLAIM_CREATED": "Nuevo reclamo registrado", "CLAIM_CLOSED": "Reclamo cerrado",
        "CLAIM_REOPENED": "Reclamo reabierto", "CLIENT_MESSAGE": "Cliente respondió un reclamo",
        "AGENT_MESSAGE": "Nuevo mensaje de soporte",
    }
    for email in recipients:
        emit(conn, email, event, claim["id_reclamo"], key, titles[event],
             "Hay una actualización registrada en el reclamo. Abre el detalle para consultarla.")


def _scope(user):
    ownership = "(n.id_destinatario=? OR (n.id_destinatario IS NULL AND lower(n.correo_cliente)=lower(?)))"
    params = [user["id_auth_user"], user["correo"]]
    if user["rol"] == "CLIENT":
        access = """(n.id_reclamo IS NULL OR EXISTS (SELECT 1 FROM reclamos r JOIN clientes c ON c.id_cliente=r.id_cliente
            WHERE r.id_reclamo=n.id_reclamo AND lower(c.correo)=lower(?))) AND
            (n.id_pedido IS NULL OR EXISTS (SELECT 1 FROM pedidos p JOIN clientes c ON c.id_cliente=p.id_cliente
            WHERE p.id_pedido=n.id_pedido AND lower(c.correo)=lower(?)))"""
        params += [user["correo"], user["correo"]]
    elif user["rol"] == "MERCHANT":
        access = """n.id_reclamo IS NULL AND n.id_pedido IS NOT NULL AND EXISTS
            (SELECT 1 FROM pedidos p JOIN comercio_operadores o ON o.id_restaurante=p.id_restaurante
             WHERE p.id_pedido=n.id_pedido AND o.id_auth_user=? AND o.activo=1)"""
        params.append(user["id_auth_user"])
    elif user["rol"] == "COURIER":
        access = """n.id_reclamo IS NULL AND n.id_pedido IS NOT NULL AND EXISTS
            (SELECT 1 FROM pedido_asignaciones a WHERE a.id_pedido=n.id_pedido AND a.id_courier=?)"""
        params.append(user["id_auth_user"])
    else:
        access = "1=1"
    return f"{ownership} AND {access}", tuple(params)


def listing(user):
    scope, params = _scope(user)
    rows = fetch_all(f"""SELECT n.*, SUM(CASE WHEN n.leida=0 THEN 1 ELSE 0 END) OVER () AS no_leidas
        FROM notificaciones n WHERE {scope}
        ORDER BY n.leida ASC,n.id_notificacion DESC LIMIT 20""", params)
    return rows, int(rows[0]["no_leidas"]) if rows else 0


def mark_read(user, notification_id=None):
    scope, params = _scope(user)
    if notification_id is not None:
        scope += " AND n.id_notificacion=?"
        params += (notification_id,)
    with transaction() as conn:
        result = conn.execute(f"UPDATE notificaciones AS n SET leida=1 WHERE {scope}", params)
        if notification_id is not None and result.rowcount != 1:
            raise DomainError("Notificación no encontrada", 404)
