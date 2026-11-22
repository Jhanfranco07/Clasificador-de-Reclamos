"""Small unit of work shared by SQLite and psycopg; no nested commits."""
from contextlib import contextmanager

from database.db_connection import get_connection, using_postgres, _insert_returning_pk
from modules.domain_errors import DomainError


@contextmanager
def transaction():
    conn = get_connection()
    try:
        if not using_postgres():
            conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def one(conn, query, params=()):
    row = conn.execute(query, params).fetchone()
    return dict(row) if row else None


def insert(conn, query, params=()):
    if using_postgres():
        row = conn.execute(_insert_returning_pk(query), params).fetchone()
        return next(iter(dict(row).values())) if row else None
    return conn.execute(query, params).lastrowid


def lock_claim(conn, claim_id):
    query = """SELECT r.*, e.nombre AS estado, c.correo AS correo_cliente
               FROM reclamos r JOIN estados_reclamo e ON e.id_estado=r.id_estado
               JOIN clientes c ON c.id_cliente=r.id_cliente WHERE r.id_reclamo=?"""
    if using_postgres():
        query += " FOR UPDATE OF r"
    claim = one(conn, query, (claim_id,))
    if not claim:
        raise DomainError("Reclamo no encontrado", 404)
    return claim


def history(conn, claim_id, previous, current, action, comment=None, actor="Soporte", actor_id=None, actor_role=None):
    return insert(conn, """INSERT INTO historial_estados
        (id_reclamo,estado_anterior,estado_nuevo,accion,comentario,usuario_responsable,actor_auth_id,actor_rol)
        VALUES (?,?,?,?,?,?,?,?)""", (claim_id, previous, current, action, comment, actor, actor_id, actor_role))
