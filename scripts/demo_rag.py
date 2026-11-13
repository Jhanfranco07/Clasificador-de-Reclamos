"""Inicia la demostración documental con una SQLite temporal y cuentas ficticias."""
import argparse
import os
from pathlib import Path
from secrets import token_urlsafe
from tempfile import TemporaryDirectory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=18100)
    parser.add_argument("--frontend-port", type=int, default=15173)
    args = parser.parse_args()
    os.environ.update(
        APP_ENV="test",
        DB_PROVIDER="sqlite",
        DATABASE_URL="",
        OPENAI_API_KEY="",
        USE_OPENAI_EMBEDDINGS="false",
        ENABLE_PGVECTOR_RAG="false",
        SMARTCLAIM_BOOTSTRAP_DEMO="0",
        PYTHON_DOTENV_DISABLED="1",
        AUTH_SECRET=token_urlsafe(48),
        CORS_ORIGINS=f"http://127.0.0.1:{args.frontend_port}",
    )

    import uvicorn
    from database import db_connection as db
    from database.repositories import crear_usuario_auth
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
        for role, label in (("CLIENT", "cliente"), ("AGENT", "agente"), ("ADMIN", "admin")):
            email = f"smartclaim-{label}@example.com"
            crear_usuario_auth(f"Demo {label}", email, hash_password(password), role)
            print(f"{role}: {email}", flush=True)
        print(f"Contraseña temporal de demostración: {password}", flush=True)
        uvicorn.run("backend.main:app", host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
