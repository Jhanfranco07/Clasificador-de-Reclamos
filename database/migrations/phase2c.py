"""Additive BF-12 migration. Existing identities and notifications remain untouched."""
from pathlib import Path

from database.db_connection import using_postgres
from database.transactions import transaction, one

VERSION = "20261106_phase2c"
ADDITIONS = {
    "reclamos": {
        "responsable_auth_id": "INTEGER REFERENCES auth_users(id_auth_user)",
        "version_asignacion": "INTEGER NOT NULL DEFAULT 0",
        "fecha_asignacion": "TEXT",
    },
    "historial_estados": {
        "actor_auth_id": "INTEGER REFERENCES auth_users(id_auth_user)",
        "actor_rol": "TEXT",
    },
    "respuestas_sugeridas": {"revisor_auth_id": "INTEGER REFERENCES auth_users(id_auth_user)"},
    "comentarios_agente": {"actor_auth_id": "INTEGER REFERENCES auth_users(id_auth_user)"},
    "notificaciones": {
        "id_destinatario": "INTEGER REFERENCES auth_users(id_auth_user)",
        "id_pedido": "INTEGER REFERENCES pedidos(id_pedido)",
        "evento": "TEXT",
        "clave_evento": "TEXT",
    },
}


def apply():
    with transaction() as conn:
        if using_postgres():
            conn.execute("SELECT pg_advisory_xact_lock(20261107)")
        if one(conn, "SELECT 1 FROM schema_migrations WHERE version=?", (VERSION,)):
            return
        for table, fields in ADDITIONS.items():
            if using_postgres():
                existing = {row["column_name"] for row in conn.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=?", (table,))}
            else:
                existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
            for name, definition in fields.items():
                if name not in existing:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")
        for statement in (Path(__file__).parent / "phase2c_shared.sql").read_text(encoding="utf-8").split(';'):
            if statement.strip():
                conn.execute(statement)
        conn.execute("INSERT INTO schema_migrations(version) VALUES (?)", (VERSION,))
