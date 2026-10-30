"""Update the identified effective row without deleting legacy configurations."""
from math import isclose

from database.db_connection import using_postgres
from database.transactions import transaction, one
from modules.domain_errors import DomainError


def save_active_config(config_id, threshold, human_review, rag, max_docs):
    with transaction() as conn:
        query = "SELECT * FROM configuracion_modelo_ia WHERE activo=1 ORDER BY id_configuracion DESC LIMIT 1"
        if using_postgres():
            query += " FOR UPDATE"
        active = one(conn, query)
        if not active or active['id_configuracion'] != config_id:
            raise DomainError("La configuración activa cambió o no existe. Recarga antes de guardar.")
        cursor = conn.execute("""UPDATE configuracion_modelo_ia SET umbral_confianza=?,
            revision_humana_obligatoria=?,usar_rag=?,max_documentos_recuperados=?,
            fecha_actualizacion=CURRENT_TIMESTAMP WHERE id_configuracion=? AND activo=1""",
            (threshold, int(human_review), int(rag), max_docs, config_id))
        if cursor.rowcount != 1:
            raise DomainError("No se actualizó la configuración. Recarga e inténtalo nuevamente.")
        saved = one(conn, "SELECT * FROM configuracion_modelo_ia WHERE id_configuracion=? AND activo=1", (config_id,))
        if (not saved or not isclose(float(saved['umbral_confianza']), threshold, rel_tol=1e-6, abs_tol=1e-7)
                or bool(saved['revision_humana_obligatoria']) != human_review
                or bool(saved['usar_rag']) != rag or saved['max_documentos_recuperados'] != max_docs):
            raise DomainError("No se pudo verificar el guardado de la configuración.")
        return saved
