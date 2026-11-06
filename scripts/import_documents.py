"""Importa el catálogo académico a una base SQLite explícita."""
import argparse
from collections import Counter
from contextlib import closing
from datetime import date
import json
from pathlib import Path
import re
import sqlite3
import unicodedata

CATEGORIES = (
    "Producto incompleto", "Producto incorrecto", "Retraso de pedido",
    "Cobro indebido", "Fraude o seguridad", "Problema con tarjeta", "Soporte general",
)
TYPES = {"FAQ", "MANUAL", "POLITICA", "PROCEDIMIENTO"}
SOURCE = "SmartClaim AI — simulación académica"
RULES = {"review": "required", "refund": "subject_to_review", "payment_data": "never_request_secrets"}


def normalized(value):
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def validate(doc):
    required = {"id", "title", "type", "category", "content", "source", "version", "updated", "status"}
    if not isinstance(doc, dict) or any(not isinstance(doc.get(k), str) or not doc[k].strip() for k in required):
        raise ValueError("Campos requeridos incompletos.")
    if not re.fullmatch(r"sc-[a-z]+-[0-9]{2}", doc["id"]):
        raise ValueError("Identificador inválido.")
    if doc["category"] not in CATEGORIES or doc["type"] not in TYPES:
        raise ValueError("Categoría o tipo inválido.")
    if len(doc["title"].strip()) < 10 or len(doc["content"].strip()) < 80:
        raise ValueError("Título ambiguo o contenido insuficiente.")
    if doc["source"] != SOURCE or doc["status"] != "vigente" or doc.get("rules") != RULES:
        raise ValueError("Procedencia, vigencia o reglas académicas incompatibles.")
    if not re.fullmatch(r"[1-9][0-9]*[.]0", doc["version"]):
        raise ValueError("Versión inválida.")
    date.fromisoformat(doc["updated"])
    if re.search(r"reembolso (garantizado|automático)|sin revisión humana|(?:solicita|pide|envía|comparte) (?:el )?(?:cvv|pin|contraseña|número completo)", normalized(doc["content"])):
        raise ValueError("El texto contiene una instrucción incompatible con las reglas.")
    return doc


def import_documents(database, catalog, dry_run=False):
    documents = json.loads(catalog.read_text(encoding="utf-8"))
    if not isinstance(documents, list):
        raise ValueError("El catálogo debe ser una lista JSON.")
    results = []
    valid = []
    for raw in documents:
        try:
            valid.append(validate(raw))
        except ValueError as exc:
            results.append({"id": raw.get("id") if isinstance(raw, dict) else None, "status": "rejected", "reason": str(exc)})
    counts = {key: Counter(normalized(doc[key]) for doc in valid) for key in ("id", "title", "content")}
    mode = "ro" if dry_run else "rw"
    with closing(sqlite3.connect(database.resolve().as_uri() + f"?mode={mode}", uri=True)) as conn, conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("BEGIN" if dry_run else "BEGIN IMMEDIATE")
        has_metadata = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE name = 'documentos_importados'"
        ).fetchone()
        known = dict(conn.execute("SELECT external_id, metadata FROM documentos_importados")) if has_metadata else {}
        current = list(conn.execute("SELECT titulo, contenido FROM documentos_base"))
        titles = {normalized(title) for title, _ in current}
        contents = {normalized(content) for _, content in current}
        pending = []
        for doc in valid:
            identifier = doc["id"]
            metadata = json.dumps(doc, ensure_ascii=False, sort_keys=True)
            if any(counts[key][normalized(doc[key])] > 1 for key in counts):
                status = "rejected"
                reason = "Identificador, título o contenido repetido en el catálogo."
            elif identifier in known:
                status = "skipped" if known[identifier] == metadata else "rejected"
                reason = "Ya importado." if status == "skipped" else "Cambio detectado. Requiere revisión y autorización."
            elif normalized(doc["title"]) in titles or normalized(doc["content"]) in contents:
                status, reason = "rejected", "Coincide con un documento existente."
            else:
                status, reason = "created", "Nuevo documento."
                pending.append((doc, metadata))
            results.append({"id": identifier, "status": status, "reason": reason})
        if not dry_run and pending:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS documentos_importados (
                    external_id TEXT PRIMARY KEY,
                    id_documento INTEGER NOT NULL UNIQUE REFERENCES documentos_base(id_documento),
                    metadata TEXT NOT NULL
                )
            """)
            for doc, metadata in pending:
                cursor = conn.execute("""
                    INSERT INTO documentos_base (titulo, tipo_documento, categoria_asociada, contenido, estado_indexacion, activo)
                    VALUES (?, ?, ?, ?, 'PENDIENTE', 1)
                """, (doc["title"].strip(), doc["type"], doc["category"], doc["content"].strip()))
                conn.execute(
                    "INSERT INTO documentos_importados (external_id, id_documento, metadata) VALUES (?, ?, ?)",
                    (doc["id"], cursor.lastrowid, metadata),
                )
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sqlite", required=True, type=Path)
    parser.add_argument("--catalog", type=Path, default=Path("data/documentos_academicos.json"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    results = import_documents(args.sqlite, args.catalog, args.dry_run)
    print(json.dumps({"dry_run": args.dry_run, "results": results}, ensure_ascii=False, indent=2))
    return int(any(row["status"] == "rejected" for row in results))


if __name__ == "__main__":
    raise SystemExit(main())
