"""Canonical claim ownership, escalation and retry ledger."""
import json
from uuid import uuid4

from database.transactions import transaction, one, lock_claim, history
from modules.domain_errors import DomainError
from modules.order_workflow import live_actor, require_role
from modules.notification_service import emit


def retry(conn, request_id, actor_id, action, payload, claim_id=None):
    previous = one(conn, "SELECT * FROM claim_commands WHERE request_id=?", (request_id,))
    if not previous:
        return None
    if (previous["actor_auth_id"] != actor_id or previous["accion"] != action or previous["payload"] != payload
            or claim_id is not None and previous["id_reclamo"] != claim_id):
        raise DomainError("La clave de solicitud corresponde a otra operación")
    return previous["id_reclamo"]


def remember(conn, request_id, actor_id, action, payload, claim_id):
    conn.execute("INSERT INTO claim_commands(request_id,id_reclamo,actor_auth_id,accion,payload) VALUES (?,?,?,?,?)",
                 (request_id, claim_id, actor_id, action, payload))


def assign(claim_id, user, target_id, version, request_id, reason, *, escalate=False):
    require_role(user, {"AGENT", "ADMIN"})
    reason = reason.strip()
    if not reason:
        raise DomainError("Indica un motivo", 422)
    action = "ESCALATE" if escalate else "ASSIGN"
    payload = json.dumps([target_id, version, reason])
    with transaction() as conn:
        user = live_actor(conn, user)
        claim = lock_claim(conn, claim_id)
        if retry(conn, request_id, user["id_auth_user"], action, payload, claim_id):
            return
        if claim["estado"] == "Cerrado" or claim["version_asignacion"] != version:
            raise DomainError("El caso está cerrado o su asignación cambió. Recarga el detalle")
        current = one(conn, "SELECT * FROM auth_users WHERE id_auth_user=? AND estado='ACTIVO' AND rol IN ('AGENT','ADMIN')",
                      (claim["responsable_auth_id"],))
        if user["rol"] == "AGENT":
            if escalate and current and current["id_auth_user"] != user["id_auth_user"]:
                raise DomainError("Solo puedes escalar un caso propio o no asignado", 403)
            if not escalate and (target_id != user["id_auth_user"] or current):
                raise DomainError("Solo puedes asumir un caso no asignado", 403)
        if escalate:
            if claim["estado"] == "Escalado":
                raise DomainError("El caso ya está escalado. Registra seguimiento o solicita reasignación")
            if target_id is None:
                target = one(conn, "SELECT * FROM auth_users WHERE rol='ADMIN' AND estado='ACTIVO' ORDER BY id_auth_user LIMIT 1")
            else:
                target = one(conn, "SELECT * FROM auth_users WHERE id_auth_user=? AND rol='ADMIN' AND estado='ACTIVO'", (target_id,))
        else:
            target = one(conn, "SELECT * FROM auth_users WHERE id_auth_user=? AND rol IN ('AGENT','ADMIN') AND estado='ACTIVO'", (target_id,))
        if not target:
            raise DomainError("No hay un responsable activo válido para esta operación", 422)
        if not escalate and claim["responsable_auth_id"] == target["id_auth_user"]:
            raise DomainError("El caso ya está asignado a este responsable")
        conn.execute("""UPDATE reclamos SET responsable_auth_id=?,responsable_asignado=?,
            fecha_asignacion=CURRENT_TIMESTAMP,version_asignacion=version_asignacion+1,
            fecha_actualizacion=CURRENT_TIMESTAMP WHERE id_reclamo=?""", (target["id_auth_user"], target["nombre"], claim_id))
        if escalate:
            from modules.claim_workflow import transition
            transition(conn, claim, "Escalado", actor=user["nombre"], role=user["rol"], comment=reason,
                       actor_id=user["id_auth_user"])
        label = "Escalamiento asignado" if escalate else "Reasignación de reclamo" if claim["responsable_auth_id"] else "Asignación de reclamo"
        history(conn, claim_id, claim["estado"], "Escalado" if escalate else claim["estado"], label,
                f"{reason}\nResponsable anterior ID {claim['responsable_auth_id'] or 'sin conciliar'} ({claim.get('responsable_asignado') or 'sin referencia'}); destinatario ID {target['id_auth_user']} ({target['nombre']})",
                user["nombre"], user["id_auth_user"], user["rol"])
        event = "CLAIM_ESCALATED" if escalate else "CLAIM_REASSIGNED" if claim["responsable_auth_id"] else "CLAIM_ASSIGNED"
        for recipient in {target["correo"], current["correo"] if current else target["correo"]}:
            emit(conn, recipient, event, claim_id, request_id, label,
                 "Se actualizó la responsabilidad de un reclamo. Consulta el detalle y su historial.")
        remember(conn, request_id, user["id_auth_user"], action, payload, claim_id)
