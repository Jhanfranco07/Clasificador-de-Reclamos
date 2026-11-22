"""Explicit, transactional extension. Never invoked by the normal application startup."""
from pathlib import Path
import re
import sqlite3

from database import db_connection as db

VERSION = "20261106_phase2b"
OLD_ROLES = "'CLIENT', 'AGENT', 'ADMIN'"
NEW_ROLES = OLD_ROLES + ", 'MERCHANT', 'COURIER'"
OLD_STATES = "'DELIVERED', 'IN_TRANSIT', 'CANCELLED', 'DELAYED', 'PREPARING'"
NEW_STATES = OLD_STATES + ", 'RECEIVED', 'ACCEPTED', 'READY_FOR_PICKUP'"


def _sqlite_constraint(conn, table, field, values):
    sequence = conn.execute("SELECT seq FROM sqlite_sequence WHERE name=?", (table,)).fetchone()
    definition = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()[0]
    definition, count = re.subn(rf"CHECK\s*\(\s*{field}\s+IN\s*\([^)]*\)\s*\)",
                               f"CHECK ({field} IN ({values}))", definition, flags=re.I)
    if count != 1:
        raise RuntimeError(f"Revisar manualmente el constraint de {table}.{field}")
    objects = conn.execute("SELECT sql FROM sqlite_master WHERE tbl_name=? AND type IN ('index','trigger') AND sql IS NOT NULL", (table,)).fetchall()
    columns = ','.join('"' + row[1] + '"' for row in conn.execute(f'PRAGMA table_info({table})'))
    definition = re.sub(rf'CREATE TABLE\s+(?:IF NOT EXISTS\s+)?["`\[]?{table}["`\]]?',
                        f'CREATE TABLE {table}_phase2b', definition, count=1, flags=re.I)
    conn.execute(definition)
    conn.execute(f"INSERT INTO {table}_phase2b ({columns}) SELECT {columns} FROM {table}")
    conn.execute(f"DROP TABLE {table}")
    conn.execute(f"ALTER TABLE {table}_phase2b RENAME TO {table}")
    if sequence:
        conn.execute("UPDATE sqlite_sequence SET seq=MAX(seq,?) WHERE name=?", (sequence[0], table))
    for obj in objects:
        conn.execute(obj[0])


def apply():
    if db.using_postgres():
        with db.get_connection() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(20261106)")
            conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
            if conn.execute("SELECT 1 FROM schema_migrations WHERE version=?", (VERSION,)).fetchone():
                conn.commit()
                return
            conn.executescript((Path(__file__).parent / "phase2b_postgres.sql").read_text(encoding="utf-8"))
            conn.commit()
        return
    conn = db.get_connection()
    try:
        # Rebuild only CHECK constraints, retaining columns, IDs, indexes and triggers.
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT DEFAULT CURRENT_TIMESTAMP)")
        if conn.execute("SELECT 1 FROM schema_migrations WHERE version=?", (VERSION,)).fetchone():
            conn.rollback()
            return
        before = list(conn.execute("PRAGMA foreign_key_check"))
        _sqlite_constraint(conn, "auth_users", "rol", NEW_ROLES)
        _sqlite_constraint(conn, "pedidos", "estado", NEW_STATES)
        for table, additions in {
            "pedidos": {"version_operativa": "INTEGER NOT NULL DEFAULT 0", "recogido_at": "TEXT", "entregado_at": "TEXT"},
            "restaurantes": {"direccion": "TEXT", "responsable": "TEXT"},
        }.items():
            existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
            for name, definition in additions.items():
                if name not in existing:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")
        script = (Path(__file__).parent / "phase2b_shared.sql").read_text(encoding="utf-8")
        for statement in script.split(';'):
            if statement.strip():
                conn.execute(statement)
        after = list(conn.execute("PRAGMA foreign_key_check"))
        if [tuple(row) for row in before] != [tuple(row) for row in after]:
            raise RuntimeError("La migración introduciría errores de integridad referencial")
        conn.execute("INSERT INTO schema_migrations(version) VALUES (?)", (VERSION,))
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def rollback_sqlite():
    """Constraint downgrade only. Retain extension tables and audit records for recovery."""
    if db.using_postgres():
        raise RuntimeError("El rollback PostgreSQL requiere revisión del operador")
    conn = db.get_connection()
    try:
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("BEGIN IMMEDIATE")
        if conn.execute("SELECT 1 FROM auth_users WHERE rol IN ('MERCHANT','COURIER')").fetchone():
            raise RuntimeError("Existen roles nuevos. Conservar datos y usar backup verificado")
        if conn.execute("SELECT 1 FROM pedidos WHERE estado IN ('RECEIVED','ACCEPTED','READY_FOR_PICKUP')").fetchone():
            raise RuntimeError("Existen pedidos nuevos. Conservar datos y usar backup verificado")
        _sqlite_constraint(conn, "auth_users", "rol", OLD_ROLES)
        _sqlite_constraint(conn, "pedidos", "estado", OLD_STATES)
        conn.execute("DELETE FROM schema_migrations WHERE version=?", (VERSION,))
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()
