"""Evalúa TF-IDF sobre el catálogo académico y una SQLite desechable."""
import argparse
from collections import defaultdict
from math import ceil
import json
from pathlib import Path
from statistics import mean, median
from tempfile import TemporaryDirectory
from time import perf_counter

from database import db_connection
from modules.rag_engine import (TFIDF_DEFAULT, TFIDF_MODES, construir_indice_tfidf,
                                dividir_en_fragmentos, recuperar_documentos_tfidf)
from database.repositories import listar_documentos, listar_fragmentos_documento
from scripts.import_documents import import_documents


def evaluate(case_file=Path('data/consultas_rag.json'), mode=TFIDF_DEFAULT):
    with TemporaryDirectory() as directory:
        db_connection.DB_PATH = Path(directory) / "rag.db"
        if db_connection.using_postgres():
            raise RuntimeError("La evaluación requiere SQLite.")
        db_connection.init_db()
        baseline = db_connection.fetch_one("SELECT COUNT(*) AS n FROM documentos_base")["n"]
        catalog = Path("data/documentos_academicos.json")
        dry = import_documents(db_connection.DB_PATH, catalog, dry_run=True)
        assert all(row["status"] == "created" for row in dry)
        assert db_connection.fetch_one("SELECT COUNT(*) AS n FROM documentos_base")["n"] == baseline
        imported = import_documents(db_connection.DB_PATH, catalog)
        repeated = import_documents(db_connection.DB_PATH, catalog)
        assert all(row["status"] == "created" for row in imported)
        assert all(row["status"] == "skipped" for row in repeated)
        identifiers = {
            row["id_documento"]: row["external_id"]
            for row in db_connection.fetch_all("SELECT id_documento, external_id FROM documentos_importados")
        }
        index = construir_indice_tfidf(forzar=True)
        documents = {doc["id_documento"]: doc for doc in listar_documentos()}
        expected_fragments = {
            (doc_id, order): text for doc_id, doc in documents.items()
            for order, text in enumerate(dividir_en_fragmentos(doc["contenido"]), 1)
        }
        actual = listar_fragmentos_documento()
        assert len({row["id_fragmento"] for row in actual}) == len(actual) == len(expected_fragments)
        for row in actual:
            doc = documents[row["id_documento"]]
            assert all(row[field] == doc[field] for field in ("titulo", "categoria_asociada", "fecha_actualizacion"))
            assert row["texto_fragmento"] == expected_fragments.pop((row["id_documento"], row["orden_fragmento"]))
        assert not expected_fragments
        cases = json.loads(case_file.read_text(encoding="utf-8"))
        misses = []
        categories = defaultdict(list)
        precision, top_one, timings, no_evidence = [], [], [], []
        if cases:
            recuperar_documentos_tfidf(cases[0]["query"], cases[0]["category"], mode=mode)
        for case in cases:
            expected = set(case["expected"])
            start = perf_counter()
            rows = recuperar_documentos_tfidf(case["query"], case["category"], mode=mode)
            timings.append((perf_counter() - start) * 1000)
            hits = [identifiers.get(row["id_documento"]) in expected for row in rows]
            if (expected and not any(hits)) or (not expected and rows):
                misses.append({"query": case["query"], "category": case["category"],
                               "expected": sorted(expected), "retrieved": [row["titulo"] for row in rows]})
            if expected:
                categories[case["category"]].append(sum(hits) / len(expected))
                precision.append(sum(hits) / 3)
                top_one.append(bool(hits and hits[0]))
            else:
                no_evidence.append(not rows)
        return {
            "provider": "tfidf",
            "mode": mode,
            "documents_before": baseline,
            "documents_after": baseline + len(imported),
            "fragments": index["fragmentos"],
            "queries": len(cases),
            "recall_at_3": mean(value for values in categories.values() for value in values),
            "precision_at_3": mean(precision),
            "top_1": mean(top_one),
            "recall_at_3_by_category": {category: mean(values) for category, values in categories.items()},
            "no_evidence_correct": sum(no_evidence),
            "no_evidence_total": len(no_evidence),
            "median_ms": median(timings),
            "p95_ms": sorted(timings)[ceil(0.95 * len(timings)) - 1],
            "misses": misses,
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=Path("data/consultas_rag.json"))
    parser.add_argument("--mode", choices=TFIDF_MODES, default=TFIDF_DEFAULT)
    args = parser.parse_args()
    print(json.dumps(evaluate(args.cases, args.mode), indent=2, ensure_ascii=False))
