"""Importa el catálogo académico a una SQLite explícita o a PostgreSQL local de pruebas."""
import argparse
from collections import Counter
from contextlib import closing, contextmanager
from datetime import date
import json
import os
from pathlib import Path
import re
import sqlite3
from modules.text_processing import normalizar_documento as normalized

CATEGORIES = (
    "Producto incompleto", "Producto incorrecto", "Retraso de pedido",
    "Cobro indebido", "Fraude o seguridad", "Problema con tarjeta", "Soporte general",
)
TYPES = {"FAQ", "MANUAL", "POLITICA", "PROCEDIMIENTO"}
SOURCE = "SmartClaim AI — simulación académica"
RULES = {"review": "required", "refund": "subject_to_review", "payment_data": "never_request_secrets"}


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


def local_test_dsn(dsn):
    """Evita que una ejecución de pruebas acepte un destino remoto."""
    from psycopg.conninfo import conninfo_to_dict, make_conninfo

    config = conninfo_to_dict(dsn)
    if (config.get("host") != "127.0.0.1"
            or not re.fullmatch(r"smartclaim_test(?:_[a-z0-9]+)?", config.get("dbname", ""))
            or config.get("hostaddr", "127.0.0.1") != "127.0.0.1"
            or not config.get("port", "").isdigit()
            or set(config) - {"host", "hostaddr", "port", "dbname", "user", "password", "sslmode"}):
        raise ValueError("Indica PostgreSQL en 127.0.0.1 con puerto explícito y base smartclaim_test.")
    return make_conninfo(dsn, hostaddr='127.0.0.1')


@contextmanager
def _import_connection(database, dry_run, postgres_dsn):
    if postgres_dsn is not None:
        from database.db_connection import PostgresConnection

        with PostgresConnection(local_test_dsn(postgres_dsn)) as conn:
            if dry_run:
                conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            else:
                conn.execute("LOCK TABLE documentos_base IN SHARE ROW EXCLUSIVE MODE")
            yield conn
            if not dry_run:
                conn.commit()
        return

    mode = "ro" if dry_run else "rw"
    with closing(sqlite3.connect(database.resolve().as_uri() + f"?mode={mode}", uri=True)) as conn, conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("BEGIN" if dry_run else "BEGIN IMMEDIATE")
        yield conn


def import_documents(database, catalog, dry_run=False, *, postgres_dsn=None, append_fragments=False):
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
    with _import_connection(database, dry_run, postgres_dsn) as conn:
        exists = ("SELECT to_regclass('documentos_importados') AS name" if postgres_dsn is not None
                  else "SELECT name FROM sqlite_master WHERE name = 'documentos_importados'")
        table = conn.execute(exists).fetchone()
        known = {
            row["external_id"]: row["metadata"]
            for row in conn.execute("SELECT external_id, metadata FROM documentos_importados")
        } if table and table["name"] else {}
        current = list(conn.execute("SELECT titulo, contenido FROM documentos_base"))
        titles = {normalized(row["titulo"]) for row in current}
        contents = {normalized(row["contenido"]) for row in current}
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
        if append_fragments and any(row["status"] == "rejected" for row in results):
            for row in results:
                if row["status"] == "created":
                    row.update(status="blocked", reason="Lote detenido por conflicto o validación.")
            return results

        if not dry_run and pending:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS documentos_importados (
                    external_id TEXT PRIMARY KEY,
                    id_documento INTEGER NOT NULL UNIQUE REFERENCES documentos_base(id_documento),
                    metadata TEXT NOT NULL
                )
            """)
            if append_fragments:
                from modules.rag_engine import dividir_en_fragmentos

            for doc, metadata in pending:
                row = conn.execute("""
                    INSERT INTO documentos_base (titulo, tipo_documento, categoria_asociada, contenido, estado_indexacion, activo)
                    VALUES (?, ?, ?, ?, ?, 1) RETURNING id_documento
                """, (doc["title"].strip(), doc["type"], doc["category"], doc["content"].strip(),
                      "INDEXADO" if append_fragments else "PENDIENTE")).fetchone()
                document_id = row["id_documento"]
                if append_fragments:
                    for order, fragment in enumerate(dividir_en_fragmentos(doc["content"]), 1):
                        conn.execute("""
                            INSERT INTO fragmentos_documento
                                (id_documento, texto_fragmento, orden_fragmento, embedding_id)
                            VALUES (?, ?, ?, ?)
                        """, (document_id, fragment, order, f"doc_{document_id}_frag_{order}"))
                conn.execute(
                    "INSERT INTO documentos_importados (external_id, id_documento, metadata) VALUES (?, ?, ?)",
                    (doc["id"], document_id, metadata),
                )
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--sqlite", type=Path)
    target.add_argument("--postgres-test", action="store_true", help="Usa SMARTCLAIM_TEST_PG_DSN.")
    parser.add_argument("--catalog", type=Path, default=Path("data/documentos_academicos.json"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--append-fragments", action="store_true",
                        help="Añade fragmentos solo para altas nuevas y cancela el lote si hay conflictos.")
    args = parser.parse_args()
    dsn = os.getenv("SMARTCLAIM_TEST_PG_DSN") if args.postgres_test else None
    if args.postgres_test and not dsn:
        parser.error("Define SMARTCLAIM_TEST_PG_DSN con el destino de pruebas local.")
    results = import_documents(args.sqlite, args.catalog, args.dry_run, postgres_dsn=dsn, append_fragments=args.append_fragments)
    print(json.dumps({"dry_run": args.dry_run, "results": results}, ensure_ascii=False, indent=2))
    return int(any(row["status"] == "rejected" for row in results))


if __name__ == "__main__":
    raise SystemExit(main())
