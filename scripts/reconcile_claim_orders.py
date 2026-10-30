"""Report historical order links; optional reconciliation only on an explicit SQLite copy."""
import argparse
import json
from pathlib import Path
import sqlite3


def reconcile(conn, apply=False):
    columns = {row[1] for row in conn.execute("PRAGMA table_info(reclamos)")}
    if apply and "id_pedido" not in columns:
        raise ValueError("Aplica primero la ampliación aditiva del esquema en la copia")
    linked_column = "id_pedido" if "id_pedido" in columns else "NULL AS id_pedido"
    rows = conn.execute(f"SELECT id_reclamo,id_cliente,codigo_pedido,{linked_column} FROM reclamos").fetchall()
    report = []
    for claim_id, customer_id, code, linked in rows:
        order = conn.execute("SELECT id_pedido,id_cliente FROM pedidos WHERE codigo_pedido=?", (code,)).fetchone()
        status = "NO_ORDER" if not order else "OWNER_MISMATCH" if order[1] != customer_id else (
            "LINKED" if linked == order[0] else "CONFLICT" if linked is not None else "MATCH_READY")
        if apply and status == "MATCH_READY":
            conn.execute("UPDATE reclamos SET id_pedido=? WHERE id_reclamo=? AND id_pedido IS NULL", (order[0], claim_id))
        report.append({"claim_id": claim_id, "order_id": order[0] if order else None, "status": status})
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sqlite", required=True, help="Ruta explícita de una copia SQLite")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backup", help="Copia de seguridad nueva, obligatoria con --apply")
    args = parser.parse_args()
    source = Path(args.sqlite).resolve()
    original = Path(__file__).resolve().parents[1] / "data/smartclaim.db"
    if args.apply and (source == original or not args.backup):
        parser.error("La aplicación requiere una copia distinta del workspace y --backup")
    if args.apply and Path(args.backup).exists():
        parser.error("El destino de backup debe ser nuevo")
    with sqlite3.connect(source.as_uri() + ("?mode=rw" if args.apply else "?mode=ro"), uri=True) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        if args.apply:
            with sqlite3.connect(Path(args.backup).resolve()) as backup:
                conn.backup(backup)
            if "id_pedido" not in {row[1] for row in conn.execute("PRAGMA table_info(reclamos)")}:
                conn.execute("ALTER TABLE reclamos ADD COLUMN id_pedido INTEGER REFERENCES pedidos(id_pedido)")
            conn.execute("BEGIN IMMEDIATE")
        result = reconcile(conn, args.apply)
        print(json.dumps({"mode": "apply-on-copy" if args.apply else "read-only", "claims": result}))


if __name__ == "__main__":
    main()
