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


def allows_automatic_database_setup():
    """Restrict automatic seeds and document synchronization to local databases."""
    from modules.config import is_production

    if is_production() or any(os.getenv(name) for name in ("RENDER", "VERCEL")):
        return False
    if not using_postgres():
        return True

    from psycopg import ProgrammingError
    from psycopg.conninfo import conninfo_to_dict

    try:
        config = conninfo_to_dict(os.environ["DATABASE_URL"])
    except ProgrammingError:
        return False
    loopback = {"127.0.0.1", "::1"}
    host = config.get("host")
    address = config.get("hostaddr") or os.getenv("PGHOSTADDR") or host
    return (host in loopback and address == host
            and not config.get("service") and not os.getenv("PGSERVICE"))


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
    def __init__(self, dsn=None):
        import psycopg
        from psycopg.rows import dict_row

        self.conn = psycopg.connect(dsn if dsn is not None else os.environ["DATABASE_URL"], row_factory=dict_row)

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

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()


class SQLiteConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc, tb):
        try:
            return super().__exit__(exc_type, exc, tb)
        finally:
            self.close()


def get_connection():
    if using_postgres():
        return PostgresConnection()

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, factory=SQLiteConnection)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def run_script(path: Path, *, transactional=False):
    with get_connection() as conn:
        script = path.read_text(encoding="utf-8")
        if transactional and not using_postgres():
            # Group demo initialization writes instead of fsync for every statement.
            script = "BEGIN IMMEDIATE;\n" + script + "\nCOMMIT;"
        conn.executescript(script)
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
        additions = {
            "pedidos": {"id_restaurante": "INTEGER REFERENCES restaurantes(id_restaurante)",
                        "notas_entrega": "TEXT", "subtotal": "REAL", "costo_delivery": "REAL", "costo_servicio": "REAL"},
            "pedido_items": {"id_producto": "INTEGER REFERENCES productos(id_producto)"},
        }
        for table, columns in additions.items():
            if table_exists(table):
                for column, definition in columns.items():
                    if not column_exists(table, column):
                        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        if table_exists("reclamos"):
            if not column_exists("reclamos", "id_pedido"):
                conn.execute("ALTER TABLE reclamos ADD COLUMN id_pedido INTEGER REFERENCES pedidos(id_pedido)")
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
        from database.migrations.phase2b import apply
        apply()
        from database.migrations.phase2c import apply as apply_phase2c
        apply_phase2c()
        return

    run_script(base_dir / "database" / "schema.sql", transactional=True)
    run_script(base_dir / "database" / "seed_data.sql", transactional=True)
    migrate_db()
    from database.migrations.phase2b import apply
    apply()
    from database.migrations.phase2c import apply as apply_phase2c
    apply_phase2c()


def ensure_hosted_postgres_identity():
    """Fail closed if the hosted service uses SQLite or an elevated database login."""
    if not using_postgres():
        raise RuntimeError("Producción requiere una conexión PostgreSQL de servicio.")
    row = fetch_one("""
        SELECT current_user = 'smartclaim_backend'
            AND session_user = current_user
            AND r.rolcanlogin
            AND NOT (r.rolsuper OR r.rolbypassrls OR r.rolcreaterole OR r.rolcreatedb OR r.rolreplication)
            AND NOT EXISTS (SELECT 1 FROM pg_auth_members WHERE member = r.oid)
            AND NOT has_schema_privilege(current_user, 'public', 'CREATE')
            AND NOT EXISTS (
                SELECT 1 FROM pg_class
                WHERE relnamespace = 'public'::regnamespace AND relowner = r.oid
            ) AS restricted
        FROM pg_roles r WHERE r.rolname = current_user
    """)
    if not row or not row["restricted"]:
        raise RuntimeError("Producción requiere el login PostgreSQL smartclaim_backend sin privilegios elevados.")


def ensure_pgvector_embedding_dimension(expected_dimension=1536):
    """Validate vector dimension without mutating persisted vectors."""
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

    raise RuntimeError(
        f"La columna rag_embeddings.embedding requiere {expected_type}. "
        "Revisa la dimensión y prepara una migración explícita con respaldo antes de iniciar."
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
