"""Inicia la demostración documental con una SQLite temporal y cuentas ficticias."""
import argparse
import os
from pathlib import Path
from secrets import token_urlsafe
from tempfile import TemporaryDirectory


def _openai_key_from_env(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError("Falta el .env local con OPENAI_API_KEY")
    key = ""
    with path.open(encoding="utf-8-sig") as source:
        for line in source:
            name, separator, value = line.strip().partition("=")
            if separator and name.strip() == "OPENAI_API_KEY":
                key = value.strip()
                if len(key) >= 2 and key[0] == key[-1] and key[0] in "\"'":
                    key = key[1:-1]
    if not key:
        raise RuntimeError("Configura OPENAI_API_KEY en el .env local antes de activar OpenAI")
    return key


def configure_demo_environment(frontend_port: int, *, enable_openai: bool = False,
                               env_file: Path | None = None) -> None:
    key = _openai_key_from_env(env_file or Path(__file__).resolve().parents[1] / ".env") if enable_openai else ""
    os.environ.update(
        APP_ENV="test",
        DB_PROVIDER="sqlite",
        DATABASE_URL="",
        OPENAI_API_KEY=key,
        USE_OPENAI_EMBEDDINGS="false",
        ENABLE_PGVECTOR_RAG="false",
        SMARTCLAIM_BOOTSTRAP_DEMO="0",
        PYTHON_DOTENV_DISABLED="1",
        AUTH_SECRET=token_urlsafe(48),
        CORS_ORIGINS=f"http://127.0.0.1:{frontend_port}",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=18100)
    parser.add_argument("--frontend-port", type=int, default=15173)
    parser.add_argument("--enable-openai", action="store_true",
                        help="Usa solo OPENAI_API_KEY del .env local para generar respuestas.")
    args = parser.parse_args()
    configure_demo_environment(args.frontend_port, enable_openai=args.enable_openai)

    import uvicorn
    from database import db_connection as db
    from database.repositories import crear_usuario_auth, registrar_cliente_publico
    from modules.rag_engine import construir_indice_tfidf
    from modules.security import hash_password
    from scripts.import_documents import import_documents

    with TemporaryDirectory(prefix="smartclaim-demo-") as directory:
        db.DB_PATH = Path(directory) / "demo.db"
        db.init_db()
        catalog = db.BASE_DIR / "data" / "documentos_academicos.json"
        results = import_documents(db.DB_PATH, catalog)
        if len(results) != 42 or any(row["status"] != "created" for row in results):
            raise RuntimeError("La importación del catálogo académico quedó incompleta.")

        construir_indice_tfidf(forzar=True)
        password = token_urlsafe(12)
        users = {}
        for role, label in (("CLIENT", "cliente"), ("MERCHANT", "comercio"),
                            ("COURIER", "repartidor"), ("AGENT", "agente"),
                            ("ADMIN", "admin")):
            email = f"smartclaim-{label}@example.com"
            if role == "CLIENT":
                users[role] = registrar_cliente_publico(
                    f"Demo {label}", email, hash_password(password)
                )["id_auth_user"]
            else:
                users[role] = crear_usuario_auth(f"Demo {label}", email, hash_password(password), role)
            print(f"{role}: {email}", flush=True)
        with db.get_connection() as conn:
            restaurant = conn.execute("SELECT id_restaurante FROM restaurantes ORDER BY id_restaurante LIMIT 1").fetchone()
            conn.execute(
                "INSERT INTO comercio_operadores "
                "(id_restaurante, id_auth_user, puede_editar_productos) VALUES (?, ?, 1)",
                (restaurant["id_restaurante"], users["MERCHANT"]),
            )
            conn.execute(
                "INSERT INTO courier_profiles (id_auth_user, disponible) VALUES (?, 1)",
                (users["COURIER"],),
            )
            conn.commit()
        print(f"Contraseña temporal de demostración: {password}", flush=True)
        uvicorn.run("backend.main:app", host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
