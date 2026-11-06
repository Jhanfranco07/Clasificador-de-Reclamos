"""Evalúa TF-IDF sobre el catálogo académico y una SQLite desechable."""
from collections import defaultdict
import json
from pathlib import Path
from statistics import mean, median
from tempfile import TemporaryDirectory
from time import perf_counter

from database import db_connection
from modules.rag_engine import construir_indice_tfidf, recuperar_documentos_tfidf
from scripts.import_documents import import_documents


def evaluate():
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
        cases = json.loads(Path("data/consultas_rag.json").read_text(encoding="utf-8"))
        categories = defaultdict(list)
        precision, top_one, timings, no_evidence = [], [], [], []
        for case in cases:
            expected = set(case["expected"])
            start = perf_counter()
            rows = recuperar_documentos_tfidf(case["query"], case["category"])
            timings.append((perf_counter() - start) * 1000)
            hits = [identifiers.get(row["id_documento"]) in expected for row in rows]
            if expected:
                categories[case["category"]].append(sum(hits) / len(expected))
                precision.append(sum(hits) / 3)
                top_one.append(bool(hits and hits[0]))
            else:
                no_evidence.append(not rows)
        return {
            "provider": "tfidf",
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
        }


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2, ensure_ascii=False))
