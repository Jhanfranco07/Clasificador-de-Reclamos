from pathlib import Path
import os
import sqlite3
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

if load_dotenv:
    load_dotenv(BASE_DIR / ".env")

import psycopg
from psycopg.rows import dict_row

SQLITE_PATH = BASE_DIR / "data" / "smartclaim.db"

TABLES = [
    ("categorias_reclamo", "id_categoria"),
    ("prioridades", "id_prioridad"),
    ("estados_reclamo", "id_estado"),
    ("usuarios", "id_usuario"),
    ("clientes", "id_cliente"),
    ("documentos_base", "id_documento"),
    ("configuracion_modelo_ia", "id_configuracion"),
    ("fragmentos_documento", "id_fragmento"),
    ("dataset_entrenamiento", "id_dataset"),
    ("reclamos", "id_reclamo"),
    ("analisis_ia", "id_analisis"),
    ("respuestas_sugeridas", "id_respuesta"),
    ("documentos_consultados", "id_documento_consultado"),
    ("historial_estados", "id_historial"),
    ("comentarios_agente", "id_comentario"),
    ("evaluacion_respuesta", "id_evaluacion"),
    ("logs_sistema", "id_log"),
]


def require_database_url():
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url or "[YOUR-PASSWORD]" in database_url:
        raise RuntimeError("DATABASE_URL no esta configurado correctamente en .env")
    return database_url


def run_sql_file(conn, path):
    sql = path.read_text(encoding="utf-8")
    for statement in [part.strip() for part in sql.split(";") if part.strip()]:
        conn.execute(statement)
    conn.commit()


def sqlite_rows(table):
    with sqlite3.connect(SQLITE_PATH) as conn:
        conn.row_factory = sqlite3.Row
        try:
            return [dict(row) for row in conn.execute(f"SELECT * FROM {table}").fetchall()]
        except sqlite3.OperationalError:
            return []


def upsert_rows(pg_conn, table, pk, rows):
    if not rows:
        return 0

    cols = list(rows[0].keys())
    placeholders = ", ".join(["%s"] * len(cols))
    col_sql = ", ".join(cols)
    update_cols = [col for col in cols if col != pk]

    if update_cols:
        update_sql = ", ".join([f"{col} = EXCLUDED.{col}" for col in update_cols])
        conflict_sql = f"ON CONFLICT ({pk}) DO UPDATE SET {update_sql}"
    else:
        conflict_sql = f"ON CONFLICT ({pk}) DO NOTHING"

    sql = f"INSERT INTO {table} ({col_sql}) VALUES ({placeholders}) {conflict_sql}"

    for row in rows:
        pg_conn.execute(sql, tuple(row[col] for col in cols))

    pg_conn.commit()
    return len(rows)


def reset_sequence_safe(pg_conn, table, pk):
    row = pg_conn.execute(f"SELECT COALESCE(MAX({pk}), 0) AS max_id FROM {table}").fetchone()
    max_id = int(row["max_id"] or 0)
    pg_conn.execute(
        "SELECT setval(pg_get_serial_sequence(%s, %s), %s, %s)",
        (table, pk, max(max_id, 1), max_id > 0),
    )


def main():
    if not SQLITE_PATH.exists():
        raise RuntimeError(f"No existe la base SQLite: {SQLITE_PATH}")

    database_url = require_database_url()

    with psycopg.connect(database_url, row_factory=dict_row) as pg_conn:
        run_sql_file(pg_conn, BASE_DIR / "database" / "postgres_schema.sql")
        run_sql_file(pg_conn, BASE_DIR / "database" / "postgres_seed_data.sql")

        print("SmartClaim AI - Migracion SQLite -> PostgreSQL")
        print("=" * 58)

        for table, pk in TABLES:
            rows = sqlite_rows(table)
            total = upsert_rows(pg_conn, table, pk, rows)
            reset_sequence_safe(pg_conn, table, pk)
            print(f"- {table}: {total} registros migrados")

        pg_conn.commit()

    print("")
    print("Migracion completada. Configura DB_PROVIDER=postgres en Render para usar Supabase.")


if __name__ == "__main__":
    main()
