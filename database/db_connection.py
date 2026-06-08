import os
import re
import sqlite3
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - dotenv is optional in local tests
    load_dotenv = None

if load_dotenv:
    load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "smartclaim.db"

POSTGRES_PK = {
    "categorias_reclamo": "id_categoria",
    "prioridades": "id_prioridad",
    "estados_reclamo": "id_estado",
    "usuarios": "id_usuario",
    "clientes": "id_cliente",
    "auth_users": "id_auth_user",
    "pedidos": "id_pedido",
    "pedido_items": "id_item",
    "restaurantes": "id_restaurante",
    "productos": "id_producto",
    "reclamos": "id_reclamo",
    "notificaciones": "id_notificacion",
    "claim_messages": "id_mensaje",
    "analisis_ia": "id_analisis",
    "documentos_base": "id_documento",
    "fragmentos_documento": "id_fragmento",
    "rag_embeddings": "id_embedding",
    "respuestas_sugeridas": "id_respuesta",
    "documentos_consultados": "id_documento_consultado",
    "configuracion_modelo_ia": "id_configuracion",
    "historial_estados": "id_historial",
    "comentarios_agente": "id_comentario",
    "evaluacion_respuesta": "id_evaluacion",
    "dataset_entrenamiento": "id_dataset",
    "logs_sistema": "id_log",
}


def using_postgres():
    provider = os.getenv("DB_PROVIDER", "").strip().lower()
    app_env = os.getenv("APP_ENV", "").strip().lower()
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url or "[YOUR-PASSWORD]" in database_url:
        return False
    return provider == "postgres" or app_env == "production"


def _adapt_query_for_postgres(query):
    adapted = query.replace("?", "%s")
    adapted = adapted.replace("INSERT OR IGNORE", "INSERT")
    adapted = adapted.replace(
        "CAST((julianday(CURRENT_TIMESTAMP) - julianday(fecha_creacion)) * 24 * 60 AS INTEGER)",
        "CAST(EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - fecha_creacion::timestamp)) / 60 AS INTEGER)",
    )
    adapted = adapted.replace(
        "CAST((julianday(COALESCE(fecha_cierre, CURRENT_TIMESTAMP)) - julianday(fecha_creacion)) * 24 * 60 AS INTEGER)",
        "CAST(EXTRACT(EPOCH FROM (COALESCE(fecha_cierre::timestamp, CURRENT_TIMESTAMP) - fecha_creacion::timestamp)) / 60 AS INTEGER)",
    )
    return adapted


def _insert_returning_pk(query):
    if "RETURNING" in query.upper():
        return query
    match = re.search(r"INSERT\s+INTO\s+([a-zA-Z_][a-zA-Z0-9_]*)", query, flags=re.IGNORECASE)
    if not match:
        return query
    table = match.group(1)
    pk = POSTGRES_PK.get(table)
    if not pk:
        return query
    return f"{query.rstrip().rstrip(';')} RETURNING {pk}"


class PostgresConnection:
    def __init__(self):
        import psycopg
        from psycopg.rows import dict_row

        self.conn = psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type:
            self.conn.rollback()
        self.conn.close()

    def execute(self, query, params=()):
        query = _adapt_query_for_postgres(query)
        return self.conn.execute(query, params)

    def executescript(self, script):
        for statement in [part.strip() for part in script.split(";") if part.strip()]:
            if statement.upper().startswith("PRAGMA"):
                continue
            self.conn.execute(statement)

    def commit(self):
        self.conn.commit()


def get_connection():
    if using_postgres():
        return PostgresConnection()

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def run_script(path: Path):
    with get_connection() as conn:
        conn.executescript(path.read_text(encoding="utf-8"))
        conn.commit()


def column_exists(table_name: str, column_name: str) -> bool:
    if using_postgres():
        row = fetch_one(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = ?
              AND column_name = ?
            """,
            (table_name, column_name),
        )
        return row is not None

    with get_connection() as conn:
        cols = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        return any(row["name"] == column_name for row in cols)


def table_exists(table_name: str) -> bool:
    if using_postgres():
        row = fetch_one(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = ?
            """,
            (table_name,),
        )
        return row is not None

    with get_connection() as conn:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        ).fetchone()
        return row is not None


def migrate_db():
    if using_postgres():
        return

    with get_connection() as conn:
        if table_exists("reclamos"):
            if not column_exists("reclamos", "responsable_asignado"):
                conn.execute("ALTER TABLE reclamos ADD COLUMN responsable_asignado TEXT")
            if not column_exists("reclamos", "fecha_cierre"):
                conn.execute("ALTER TABLE reclamos ADD COLUMN fecha_cierre TEXT")
            if not column_exists("reclamos", "tiempo_atencion_minutos"):
                conn.execute("ALTER TABLE reclamos ADD COLUMN tiempo_atencion_minutos INTEGER")

        if table_exists("respuestas_sugeridas"):
            if not column_exists("respuestas_sugeridas", "respuesta_editada"):
                conn.execute("ALTER TABLE respuestas_sugeridas ADD COLUMN respuesta_editada TEXT")

        conn.commit()


def init_db():
    base_dir = Path(__file__).resolve().parent.parent
    if using_postgres():
        run_script(base_dir / "database" / "postgres_schema.sql")
        ensure_pgvector_embedding_dimension()
        run_script(base_dir / "database" / "postgres_seed_data.sql")
        return

    run_script(base_dir / "database" / "schema.sql")
    run_script(base_dir / "database" / "seed_data.sql")
    migrate_db()


def ensure_pgvector_embedding_dimension(expected_dimension=1536):
    """Keep the persisted pgvector column compatible with OpenAI embeddings."""
    if not using_postgres():
        return

    row = fetch_one(
        """
        SELECT format_type(a.atttypid, a.atttypmod) AS vector_type
        FROM pg_attribute a
        JOIN pg_class c ON c.oid = a.attrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relname = 'rag_embeddings'
          AND a.attname = 'embedding'
          AND a.attnum > 0
          AND NOT a.attisdropped
        """
    )
    expected_type = f"vector({int(expected_dimension)})"
    if not row or row.get("vector_type") == expected_type:
        return

    # Existing vectors cannot be resized safely. They are regenerated by reindexing.
    execute("DELETE FROM rag_embeddings")
    execute("DROP INDEX IF EXISTS idx_rag_embeddings_vector")
    execute(
        f"ALTER TABLE rag_embeddings ALTER COLUMN embedding TYPE {expected_type}"
    )
    execute(
        """
        CREATE INDEX IF NOT EXISTS idx_rag_embeddings_vector
        ON rag_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)
        """
    )


def fetch_all(query, params=()):
    with get_connection() as conn:
        query = _adapt_query_for_postgres(query) if using_postgres() else query
        return [dict(row) for row in conn.execute(query, params).fetchall()]


def fetch_one(query, params=()):
    with get_connection() as conn:
        query = _adapt_query_for_postgres(query) if using_postgres() else query
        row = conn.execute(query, params).fetchone()
        return dict(row) if row else None


def execute(query, params=()):
    with get_connection() as conn:
        if using_postgres():
            query = _insert_returning_pk(_adapt_query_for_postgres(query))
            cur = conn.execute(query, params)
            row = cur.fetchone() if "RETURNING" in query.upper() else None
            conn.commit()
            if row:
                return next(iter(dict(row).values()))
            return 0

        cur = conn.execute(query, params)
        conn.commit()
        return cur.lastrowid
