import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "smartclaim.db"

def get_connection():
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
    with get_connection() as conn:
        cols = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        return any(row["name"] == column_name for row in cols)

def table_exists(table_name: str) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        ).fetchone()
        return row is not None

def migrate_db():
    """Aplica cambios incrementales para que una base existente no falle al actualizar el proyecto."""
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
    run_script(base_dir / "database" / "schema.sql")
    run_script(base_dir / "database" / "seed_data.sql")
    migrate_db()

def fetch_all(query, params=()):
    with get_connection() as conn:
        return [dict(row) for row in conn.execute(query, params).fetchall()]

def fetch_one(query, params=()):
    with get_connection() as conn:
        row = conn.execute(query, params).fetchone()
        return dict(row) if row else None

def execute(query, params=()):
    with get_connection() as conn:
        cur = conn.execute(query, params)
        conn.commit()
        return cur.lastrowid
