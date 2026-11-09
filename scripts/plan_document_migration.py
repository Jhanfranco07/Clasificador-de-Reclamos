"""Plan documental en lectura para una copia local de PostgreSQL."""
import argparse
from collections import Counter, defaultdict
import json
import os
from pathlib import Path

from database.db_connection import PostgresConnection
from modules.rag_engine import dividir_en_fragmentos
from modules.text_processing import normalizar_documento
from scripts.import_documents import local_test_dsn, validate


FIELDS = {"title": "titulo", "type": "tipo_documento", "category": "categoria_asociada", "content": "contenido"}


def _document_fields(doc):
    return {column: doc[key].strip() for key, column in FIELDS.items()}


def _fragment_changes(doc, fragments, embeddings):
    expected = dict(enumerate(dividir_en_fragmentos(doc["content"]), 1))
    retained = set()
    obsolete = []
    invalidated = []
    regenerate = set()
    for fragment in fragments:
        order = fragment["orden_fragmento"]
        fid = fragment["id_fragmento"]
        embedding = embeddings.get(fid)
        if order in retained or expected.get(order) != fragment["texto_fragmento"]:
            obsolete.append(fid)
            if embedding:
                invalidated.append(embedding["id_embedding"])
            continue
        retained.add(order)
        compatible = (
            embedding is not None
            and embedding["id_documento"] == fragment["id_documento"]
            and embedding["dimension"] == 1536
            and embedding["texto_fragmento"] == expected[order]
            and all(embedding[column] == doc[key].strip()
                    for key, column in FIELDS.items() if key != "content")
        )
        if not compatible:
            regenerate.add(order)
            if embedding:
                invalidated.append(embedding["id_embedding"])
    return {
        "obsolete_fragment_ids": obsolete,
        "new_fragment_orders": sorted(expected.keys() - retained),
        "invalidated_embedding_ids": invalidated,
        "embedding_orders_to_regenerate": sorted(regenerate | (expected.keys() - retained)),
    }


def plan_document_migration(dsn, catalog):
    data = json.loads(catalog.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("El catálogo debe ser una lista.")
    incoming = [validate(doc) for doc in data]
    counts = {key: Counter(normalizar_documento(doc[key]) for doc in incoming)
              for key in ("id", "title", "content")}

    with PostgresConnection(local_test_dsn(dsn)) as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        documents = {row["id_documento"]: row for row in conn.execute(
            "SELECT id_documento, titulo, tipo_documento, categoria_asociada, contenido, activo FROM documentos_base"
        )}
        table = conn.execute("SELECT to_regclass('documentos_importados') AS name").fetchone()
        known = {row["external_id"]: row for row in conn.execute(
            "SELECT external_id, id_documento, metadata FROM documentos_importados"
        )} if table["name"] else {}
        fragments = defaultdict(list)
        for row in conn.execute("SELECT * FROM fragmentos_documento ORDER BY id_fragmento"):
            fragments[row["id_documento"]].append(row)
        embeddings = {row["id_fragmento"]: row for row in conn.execute("""
            SELECT id_embedding, id_fragmento, id_documento, dimension, titulo, tipo_documento,
                   categoria_asociada, texto_fragmento
            FROM rag_embeddings
        """)}
        sequence = conn.execute("""
            SELECT pg_sequence_last_value(pg_get_serial_sequence('documentos_base', 'id_documento')::regclass) AS last_value
        """).fetchone()["last_value"]

        results = []
        for doc in incoming:
            identifier = doc["id"]
            link = known.get(identifier)
            local_id = link["id_documento"] if link else None
            row = {"id": identifier, "local_id": local_id, "target_version": doc["version"]}
            collisions = any(
                current_id != local_id and (
                    normalizar_documento(current["titulo"]) == normalizar_documento(doc["title"])
                    or normalizar_documento(current["contenido"]) == normalizar_documento(doc["content"])
                ) for current_id, current in documents.items()
            )
            if any(counts[key][normalizar_documento(doc[key])] > 1 for key in counts) or collisions:
                row.update(action="conflict", reason="ID, título o contenido duplicado, o coincidencia sin asociación verificada.")
            elif not link:
                row.update(action="create", **_fragment_changes(doc, [], embeddings))
            else:
                try:
                    previous = validate(json.loads(link["metadata"]))
                    current = documents[local_id]
                    if previous["id"] != identifier or not current["activo"] or any(
                        current[column] != value for column, value in _document_fields(previous).items()
                    ):
                        raise ValueError("El documento actual difiere de sus metadatos registrados.")
                    row["previous_version"] = previous["version"]
                    if previous == doc:
                        row.update(action="keep", **_fragment_changes(doc, fragments[local_id], embeddings))
                    elif int(doc["version"].split(".")[0]) > int(previous["version"].split(".")[0]):
                        row.update(action="review_upgrade",
                                   **_fragment_changes(doc, fragments[local_id], embeddings))
                    else:
                        raise ValueError("Versión igual con cambios o versión anterior.")
                except (ValueError, KeyError, TypeError) as exc:
                    row.update(action="conflict", reason=str(exc))
            results.append(row)

        max_id = max(documents, default=0)
        return {
            "read_only": True,
            "counts": dict(Counter(row["action"] for row in results)),
            "existing_documents": len(documents),
            "existing_fragments": sum(map(len, fragments.values())),
            "existing_embeddings": len(embeddings),
            "document_sequence_last_value": sequence,
            "max_document_id": max_id,
            "sequence_needs_review": bool(max_id and (sequence is None or sequence < max_id)),
            "results": results,
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=Path("data/documentos_academicos.json"))
    args = parser.parse_args()
    dsn = os.getenv("SMARTCLAIM_TEST_PG_DSN")
    if not dsn:
        parser.error("Define SMARTCLAIM_TEST_PG_DSN para la copia local.")
    plan = plan_document_migration(dsn, args.catalog)
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    return int(bool(plan["counts"].get("conflict") or plan["sequence_needs_review"]))


if __name__ == "__main__":
    raise SystemExit(main())
