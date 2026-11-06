"""Draft editing and exactly-once publication inside one database transaction."""
from database.transactions import transaction, one, insert, lock_claim, history
from modules.domain_errors import DomainError



def _actor(conn, actor_id):
    identity = one(conn, "SELECT * FROM auth_users WHERE CAST(id_auth_user AS TEXT)=?", (str(actor_id),))
    if identity:
        from modules.order_workflow import live_actor, require_role
        identity = live_actor(conn, identity)
        require_role(identity, {"AGENT", "ADMIN"})
    return identity


def _locked_response(conn, response_id):
    response = one(conn, "SELECT * FROM respuestas_sugeridas WHERE id_respuesta=?", (response_id,))
    if not response:
        raise DomainError("Respuesta no encontrada", 404)
    claim = lock_claim(conn, response["id_reclamo"])
    # Re-read after acquiring the claim lock, including a concurrent approval.
    return one(conn, "SELECT * FROM respuestas_sugeridas WHERE id_respuesta=?", (response_id,)), claim


def edit_draft(response_id, text, actor="Soporte", actor_id=None):
    with transaction() as conn:
        identity = _actor(conn, actor_id)
        response, claim = _locked_response(conn, response_id)
        if claim["estado"] == "Cerrado" or response["estado_revision"] in {"APROBADA", "ENVIADA"}:
            raise DomainError("La respuesta publicada o de un reclamo cerrado no puede editarse como borrador")
        conn.execute("""UPDATE respuestas_sugeridas SET respuesta_editada=?,
                        respuesta_final=NULL, estado_revision='EDITADA' WHERE id_respuesta=?""", (text, response_id))
        history(conn, claim["id_reclamo"], claim["estado"], claim["estado"],
                "Edición de borrador", actor=actor, actor_id=actor_id, actor_role=identity["rol"] if identity else None)


def publish(response_id, text=None, actor="Soporte", actor_id="support"):
    with transaction() as conn:
        # Legacy internal callers may lack an auth identity. Never infer it from a name.
        identity = _actor(conn, actor_id)
        response, claim = _locked_response(conn, response_id)
        if response["estado_revision"] in {"APROBADA", "ENVIADA"}:
            return False  # Retry is a no-op, including after the case was closed.
        if claim["estado"] == "Cerrado":
            raise DomainError("Reabre el reclamo antes de publicar una respuesta")
        final = (text or response["respuesta_editada"] or response["respuesta_generada"]).strip()
        if len(final) < 5:
            raise DomainError("La respuesta debe contener al menos cinco caracteres", 422)
        conn.execute("""UPDATE respuestas_sugeridas SET respuesta_final=?,
                        estado_revision='APROBADA',fecha_revision=CURRENT_TIMESTAMP,revisor_auth_id=?
                        WHERE id_respuesta=?""", (final, identity["id_auth_user"] if identity else None, response_id))
        insert(conn, """INSERT INTO claim_messages(id_reclamo,sender_type,sender_id,mensaje)
                        VALUES (?,'agent',?,?)""", (claim["id_reclamo"], str(actor_id), final))
        from modules.notification_service import emit
        emit(conn, claim["correo_cliente"], "CLAIM_PUBLISHED", claim["id_reclamo"], response_id,
             "Respuesta de soporte disponible", "Soporte publicó una respuesta en tu reclamo.", inserter=insert)
        from modules.claim_workflow import transition
        changed = transition(conn, claim, "Respondido", mode="publish", actor=actor,
                             actor_id=identity["id_auth_user"] if identity else None,
                             role=identity["rol"] if identity else "AGENT")
        if not changed:
            history(conn, claim["id_reclamo"], claim["estado"], claim["estado"], "Envio de respuesta", actor=actor,
                    actor_id=identity["id_auth_user"] if identity else None, actor_role=identity["rol"] if identity else None)
        return True
