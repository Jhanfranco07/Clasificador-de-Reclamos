"""Existing claim states with explicit permission and consistency guards.

No deadlines, refund decisions or customer-acceptance rules are introduced here.
"""
from database.transactions import one, history
from modules.domain_errors import DomainError

STAFF = {"AGENT", "ADMIN"}
ACTIVE = {"Nuevo", "Analizado por IA", "En revision", "Respondido", "Escalado"}


def canonical(state):
    return state.replace("En revisión", "En revision")


def transition(conn, claim, target, *, mode="staff", actor="Soporte", role="AGENT", comment=None):
    previous, target = canonical(claim["estado"]), canonical(target)
    if target not in ACTIVE | {"Cerrado"}:
        raise DomainError("Estado de reclamo no válido", 422)
    if mode == "reopen":
        if role not in STAFF | {"CLIENT"}:
            raise DomainError("No tienes permisos", 403)
        if previous != "Cerrado" or target != "En revision":
            raise DomainError("Solo se puede reabrir un reclamo cerrado")
    else:
        if previous == "Cerrado":
            raise DomainError("El reclamo está cerrado. Reábrelo antes de continuar.")
        if mode == "analysis":
            if role != "SYSTEM":
                raise DomainError("Operación de análisis no autorizada", 403)
            if previous in {"Respondido", "Escalado"}:
                target = previous  # A new suggestion cannot undo an operational decision.
        elif mode == "client_message":
            if role != "CLIENT" or target != "En revision":
                raise DomainError("Transición no autorizada", 403)
        elif role not in STAFF:
            raise DomainError("No tienes permisos para cambiar el estado", 403)
        if target == "Nuevo" or (target == "Analizado por IA" and mode != "analysis"):
            raise DomainError("La transición solicitada no corresponde a esta operación")
    if target == "Respondido" and not one(conn, """SELECT id_mensaje FROM claim_messages
            WHERE id_reclamo=? AND sender_type='agent' AND is_internal=0 LIMIT 1""", (claim["id_reclamo"],)):
        raise DomainError("No se puede marcar respondido sin una respuesta publicada")
    if target == "Cerrado" and not (comment or "").strip():
        raise DomainError("Indica un motivo de cierre administrativo", 422)
    if previous == target and mode != "analysis":
        if mode in {"client_message", "agent_message", "publish"}:
            conn.execute("UPDATE reclamos SET fecha_actualizacion=CURRENT_TIMESTAMP WHERE id_reclamo=?", (claim["id_reclamo"],))
        return False
    state = one(conn, "SELECT id_estado FROM estados_reclamo WHERE nombre=?", (target,))
    if not state:
        raise DomainError("El estado requerido no está configurado", 409)
    if target == "Cerrado":
        conn.execute("""UPDATE reclamos SET id_estado=?,fecha_cierre=CURRENT_TIMESTAMP,
            tiempo_atencion_minutos=CAST((julianday(CURRENT_TIMESTAMP) - julianday(fecha_creacion)) * 24 * 60 AS INTEGER),
            fecha_actualizacion=CURRENT_TIMESTAMP WHERE id_reclamo=?""", (state["id_estado"], claim["id_reclamo"]))
    else:
        conn.execute("""UPDATE reclamos SET id_estado=?,fecha_cierre=NULL,tiempo_atencion_minutos=NULL,
                        fecha_actualizacion=CURRENT_TIMESTAMP WHERE id_reclamo=?""", (state["id_estado"], claim["id_reclamo"]))
    action = {"reopen": "Reapertura de reclamo", "analysis": "Análisis IA", "publish": "Envio de respuesta",
              "client_message": "Respuesta del cliente", "agent_message": "Respuesta del agente"}.get(mode, "Cambio de estado")
    if target == "Cerrado":
        action = "Cierre de reclamo"
    history(conn, claim["id_reclamo"], previous, target, action, comment, actor)
    return True


def record_message(claim_id, text, user):
    from database.transactions import transaction, insert, lock_claim
    if len(text.strip()) < 2:
        raise DomainError("El mensaje debe contener al menos dos caracteres", 422)
    with transaction() as conn:
        claim = lock_claim(conn, claim_id)
        client = user["rol"] == "CLIENT"
        if client and claim["correo_cliente"].lower() != user["correo"].lower():
            raise DomainError("No tienes acceso a este reclamo", 403)
        if claim["estado"] == "Cerrado":
            raise DomainError("Reabre el reclamo antes de responder")
        insert(conn, """INSERT INTO claim_messages(id_reclamo,sender_type,sender_id,mensaje)
                        VALUES (?,?,?,?)""", (claim_id,"client" if client else "agent",str(user["id_auth_user"]),text.strip()))
        changed = transition(conn, claim, "En revision" if client else "Respondido",
                             mode="client_message" if client else "agent_message", actor=user["nombre"], role=user["rol"])
        if not changed:
            history(conn, claim_id, claim["estado"], claim["estado"],
                    "Respuesta del cliente" if client else "Respuesta del agente", actor=user["nombre"])
