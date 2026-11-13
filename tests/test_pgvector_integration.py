"""Pruebas optativas contra PostgreSQL con pgvector en loopback."""
import json
from pathlib import Path

import psycopg
import pytest

from database import db_connection as db
from database import repositories as repo
from modules import openai_embeddings, rag_engine
from scripts.import_documents import import_documents, local_test_dsn


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
    before_rebuild = rag_engine.recuperar_documentos(query, category)
    assert all(row["id_documento"] != 4 and row["vector_store"] == "tfidf" for row in before_rebuild)
    rag_engine.construir_indice_tfidf(forzar=True)
    assert repo.contar_embeddings_rag() == 1
    replacement = rag_engine.recuperar_documentos(query, category)[0]
    assert replacement["id_documento"] == 4
    assert replacement["id_fragmento"] != missing["id_fragmento"]
    assert replacement["vector_store"] == "tfidf"


def test_vector_dimension_mismatch_preserves_existing_data(vector_db):
    db.execute("ALTER TABLE rag_embeddings ALTER COLUMN embedding TYPE vector(2)")
    fragment = repo.listar_fragmentos_documento()[0]
    repo.crear_embedding_rag(fragment, "sintetico", 2, [1, 0])
    with pytest.raises(RuntimeError, match="vector\\(1536\\)"):
        db.ensure_pgvector_embedding_dimension()
    assert repo.contar_embeddings_rag() == 1
    assert db.fetch_one("SELECT vector_dims(embedding) AS n FROM rag_embeddings")["n"] == 2


def test_read_only_migration_plan_preserves_versions_and_identifies_vectors(vector_db, tmp_path):
    from scripts.plan_document_migration import plan_document_migration

    catalog = json.loads(Path("data/documentos_academicos.json").read_text(encoding="utf-8"))
    target = next(doc for doc in catalog if doc["version"] == "2.0")
    original = {**target, "version": "1.0", "content": "Texto académico anterior para verificar el cambio de versión sin modificar la base de datos."}
    path = tmp_path / "old.json"
    path.write_text(json.dumps([original]), encoding="utf-8")
    assert import_documents(None, path, postgres_dsn=vector_db)[0]["status"] == "created"
    rag_engine.construir_indice_tfidf(forzar=True)
    local = db.fetch_one("SELECT id_documento FROM documentos_importados WHERE external_id = ?", (target["id"],))
    fragment = next(frag for frag in repo.listar_fragmentos_documento() if frag["id_documento"] == local["id_documento"])
    repo.crear_embedding_rag(fragment, "sintetico", 1536, [1.0] + [0.0] * 1535)
    final = tmp_path / "new.json"
    final.write_text(json.dumps(catalog), encoding="utf-8")
    before = repo.listar_documentos()
    plan = plan_document_migration(vector_db, final)
    assert plan["counts"] == {"create": 41, "review_upgrade": 1}
    revision = next(row for row in plan["results"] if row["action"] == "review_upgrade")
    assert revision["local_id"] == local["id_documento"]
    assert revision["obsolete_fragment_ids"] == [fragment["id_fragmento"]]
    assert revision["embedding_orders_to_regenerate"] == [1]
    assert len(revision["invalidated_embedding_ids"]) == 1
    assert repo.listar_documentos() == before
    assert repo.contar_embeddings_rag() == 1

    db.execute("UPDATE documentos_base SET contenido = ? WHERE id_documento = ?",
               ("Edición manual fuera del catálogo.", local["id_documento"]))
    assert plan_document_migration(vector_db, final)["counts"]["conflict"] == 1
