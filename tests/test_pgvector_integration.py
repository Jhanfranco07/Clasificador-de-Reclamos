"""Pruebas optativas contra PostgreSQL con pgvector en loopback."""
import json
import os
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
import pytest

from database import db_connection as db
from database import repositories as repo
from modules import openai_embeddings, rag_engine
from scripts.import_documents import import_documents, local_test_dsn


@pytest.fixture
def vector_db(monkeypatch):
    base = os.getenv("SMARTCLAIM_TEST_PG_DSN")
    if not base:
        pytest.skip("SMARTCLAIM_TEST_PG_DSN no configurado.")
    base = local_test_dsn(base)
    name = "smartclaim_test_" + uuid4().hex
    with psycopg.connect(base, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        try:
            dsn = make_conninfo(base, dbname=name)
            monkeypatch.setenv("DATABASE_URL", dsn)
            monkeypatch.setenv("DB_PROVIDER", "postgres")
            monkeypatch.setenv("APP_ENV", "test")
            monkeypatch.setenv("ENABLE_PGVECTOR_RAG", "true")
            monkeypatch.delenv("OPENAI_API_KEY", raising=False)
            db.init_db()
            yield dsn
        finally:
            admin.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))


def test_local_dsn_guard_rejects_external_or_ambiguous_target():
    for dsn in (
        "host=example.org port=5432 dbname=smartclaim_test",
        "host=127.0.0.1 hostaddr=198.51.100.1 port=5432 dbname=smartclaim_test",
        "host=127.0.0.1 port=5432 dbname=production",
    ):
        with pytest.raises(ValueError):
            local_test_dsn(dsn)


def test_postgres_import_idempotence_and_rollback(vector_db, tmp_path):
    catalog = Path("data/documentos_academicos.json")
    load = lambda source, dry=False: import_documents(None, source, dry, postgres_dsn=vector_db)
    assert len(repo.listar_documentos()) == 18
    assert {row["status"] for row in load(catalog, True)} == {"created"}
    assert not db.table_exists("documentos_importados")
    assert {row["status"] for row in load(catalog)} == {"created"}
    assert {row["status"] for row in load(catalog)} == {"skipped"}
    docs = repo.listar_documentos()
    assert len(docs) == 60
    assert len({row["titulo"] for row in docs}) == 60
    assert {row["categoria_asociada"] for row in docs} == {
        row["nombre"] for row in db.fetch_all("SELECT nombre FROM categorias_reclamo")
    }
    assert next(row for row in docs if row["id_documento"] == 4)["titulo"].startswith("FAQ sobre pedido incompleto")

    first = json.loads(catalog.read_text(encoding="utf-8"))[0]
    records = [{**first, "id": f"sc-faltantes-{number}", "title": f"Procedimiento de prueba {number}",
                "content": f"{first['content']} Comprobación aislada {number}."}
               for number in (90, 91)]
    broken = tmp_path / "rollback.json"
    broken.write_text(json.dumps(records), encoding="utf-8")
    db.execute("ALTER TABLE documentos_importados ADD CHECK (external_id <> 'sc-faltantes-91')")
    with pytest.raises(psycopg.errors.CheckViolation):
        load(broken)
    assert repo.listar_documentos() == docs
    assert db.fetch_one("SELECT COUNT(*) AS total FROM documentos_importados")["total"] == 42


def test_pgvector_filters_stale_rows_and_falls_back(vector_db, monkeypatch):
    rag_engine.construir_indice_tfidf(forzar=True)
    rows = repo.listar_fragmentos_documento()
    missing = next(row for row in rows if row["id_documento"] == 4)
    fraud = next(row for row in rows if row["id_documento"] == 5)
    vector = [1.0] + [0.0] * 1535
    orthogonal = [0.0, 1.0] + [0.0] * 1534
    query = "productos faltantes en pedido incompleto"
    category = "Producto incompleto"
    monkeypatch.setattr(openai_embeddings, "create_embeddings", lambda texts: [vector for _ in texts])
    monkeypatch.setattr(openai_embeddings, "search", lambda *args, **kwargs: [])
    assert rag_engine.recuperar_documentos(query, category)[0]["vector_store"] == "tfidf"
    with pytest.raises(psycopg.errors.DataException):
        repo.crear_embedding_rag(missing, openai_embeddings.MODEL, 2, [1, 0])
    repo.crear_embedding_rag(fraud, openai_embeddings.MODEL, 1536, vector)
    assert rag_engine.recuperar_documentos(query, category)[0]["vector_store"] == "tfidf"
    repo.crear_embedding_rag(missing, openai_embeddings.MODEL, 1536, orthogonal)
    assert rag_engine.recuperar_documentos(query, category)[0]["vector_store"] == "tfidf"
    assert rag_engine.recuperar_documentos("zqxvv brrrt", category) == []

    db.execute("UPDATE rag_embeddings SET embedding = ?::vector WHERE id_fragmento = ?",
               ("[" + ",".join(map(str, vector)) + "]", missing["id_fragmento"]))
    result = rag_engine.recuperar_documentos(query, category)[0]
    assert result["vector_store"] == "supabase_pgvector"
    assert float(result["score"]) == pytest.approx(1.0)
    for field in ("id_documento", "id_fragmento", "titulo", "categoria_asociada", "texto_fragmento"):
        assert result[field] == missing[field]

    def unavailable(*args, **kwargs):
        raise psycopg.OperationalError("Conexión vectorial interrumpida")

    with monkeypatch.context() as patched:
        patched.setattr(rag_engine, "buscar_embeddings_rag", unavailable)
        assert rag_engine.recuperar_documentos(query, category)[0]["vector_store"] == "tfidf"

    repo.actualizar_documento_base(4, missing["titulo"], "FAQ", category,
                                  "Productos faltantes en pedido incompleto. Verificar cantidad y recibo.")
    assert rag_engine.recuperar_documentos(query, category) == []
    rag_engine.construir_indice_tfidf(forzar=True)
    assert repo.contar_embeddings_rag() == 1
    replacement = rag_engine.recuperar_documentos(query, category)[0]
    assert replacement["id_documento"] == 4
    assert replacement["id_fragmento"] != missing["id_fragmento"]
    assert replacement["vector_store"] == "tfidf"
