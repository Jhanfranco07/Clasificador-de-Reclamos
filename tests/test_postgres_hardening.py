"""Security and upgrade checks against a disposable loopback cluster."""
import json
from pathlib import Path

from fastapi.testclient import TestClient
import psycopg
from psycopg import errors, sql
from psycopg.rows import dict_row
import pytest

from database import db_connection as db
from scripts.import_documents import import_documents
from test_phase1_acceptance import auth, new_claim

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "database/migrations"


def run_sql(conn, filename):
    conn.execute((MIGRATIONS / filename).read_text(encoding="utf-8"))


def test_direct_roles_denied_and_privileged_backend_rejected(hardening_postgres, vector_db):
    with psycopg.connect(vector_db, autocommit=True) as owner:
        owner.execute("""
            GRANT USAGE ON SCHEMA public TO PUBLIC, anon, authenticated;
            GRANT ALL ON ALL TABLES IN SCHEMA public TO anon, authenticated, service_role;
            GRANT SELECT (password_hash) ON auth_users TO PUBLIC;
            GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated;
        """)
        run_sql(owner, "integrated_database_security.sql")
        run_sql(owner, "integrated_database_security.sql")
        for role in ("anon", "authenticated", "service_role"):
            owner.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(role)))
            try:
                for statement in (
                    "SELECT password_hash FROM public.auth_users",
                    "UPDATE public.auth_users SET rol = 'ADMIN' WHERE false",
                    "SELECT * FROM public.reclamos",
                    "DELETE FROM public.rag_embeddings WHERE false",
                    "SELECT nextval('public.documentos_base_id_documento_seq')",
                ):
                    with pytest.raises(errors.InsufficientPrivilege):
                        owner.execute(statement)
            finally:
                owner.execute("RESET ROLE")

        assert owner.execute("""
            SELECT bool_and(relrowsecurity AND relforcerowsecurity)
            FROM pg_class WHERE oid IN ('public.auth_users'::regclass, 'public.rag_embeddings'::regclass)
        """).fetchone()[0]
        owner.execute("SET ROLE smartclaim_backend")
        assert owner.execute("SELECT count(*) FROM pedidos").fetchone()[0] == 0
        for statement in (
            "DELETE FROM reclamos WHERE false",
            "UPDATE rag_embeddings SET dimension = 1 WHERE false",
            "TRUNCATE TABLE documentos_base",
            "CREATE TABLE public.escalation_probe (id int)",
            "ALTER TABLE pedidos DISABLE ROW LEVEL SECURITY",
        ):
            with pytest.raises(errors.InsufficientPrivilege):
                owner.execute(statement)
        owner.execute("RESET ROLE")

    with pytest.raises(RuntimeError, match="smartclaim_backend"):
        db.ensure_hosted_postgres_identity()


def test_legacy_upgrade_sequence_integrity_and_append_only(hardening_postgres, tmp_path):
    with psycopg.connect(hardening_postgres, autocommit=True, row_factory=dict_row) as owner:
        owner.execute((ROOT / "database/postgres_schema.sql").read_text(encoding="utf-8"))
        # Match the missing production Phase 1 columns before inserting data.
        owner.execute("""
            ALTER TABLE pedidos DROP id_restaurante, DROP notas_entrega,
                DROP subtotal, DROP costo_delivery, DROP costo_servicio;
            ALTER TABLE pedido_items DROP id_producto;
            ALTER TABLE reclamos DROP id_pedido;
        """)
        owner.execute((ROOT / "database/postgres_seed_data.sql").read_text(encoding="utf-8"))
        owner.execute("""
            SELECT setval('documentos_base_id_documento_seq', 6);
            SELECT setval('fragmentos_documento_id_fragmento_seq', 3, false);
            SELECT setval('categorias_reclamo_id_categoria_seq', 500, false);
            INSERT INTO rag_embeddings (id_fragmento, id_documento, modelo_embedding, dimension,
                embedding, texto_fragmento, titulo, tipo_documento, categoria_asociada)
            SELECT f.id_fragmento, d.id_documento, 'fixture', 1536, array_fill(0.1::real, ARRAY[1536])::vector,
                f.texto_fragmento, d.titulo, d.tipo_documento, d.categoria_asociada
            FROM fragmentos_documento f JOIN documentos_base d USING (id_documento);
            INSERT INTO clientes (nombre, correo) VALUES ('Titular', 'owner@example.test'), ('Otro', 'other@example.test');
            INSERT INTO pedidos (codigo_pedido,id_cliente,tienda_nombre,direccion_entrega)
            SELECT 'ORDER-LAB',id_cliente,'Comercio sintético','Dirección sintética' FROM clientes WHERE correo='owner@example.test';
            INSERT INTO reclamos (codigo_reclamo,id_cliente,codigo_pedido,canal_venta,descripcion,id_estado)
            SELECT 'CLAIM-LAB',id_cliente,'ORDER-LAB','WEB','Texto sintético',
                (SELECT min(id_estado) FROM estados_reclamo) FROM clientes WHERE correo='other@example.test';
        """)
        snapshots = {}
        for table, key in (("documentos_base", "id_documento"), ("fragmentos_documento", "id_fragmento"),
                           ("rag_embeddings", "id_embedding")):
            rows = owner.execute(sql.SQL("SELECT {} AS id, to_jsonb(t) AS row FROM {} t").format(
                sql.Identifier(key), sql.Identifier(table))).fetchall()
            snapshots[table] = {row["id"]: row["row"] for row in rows}

        owner.execute("CREATE TABLE sequence_rollback_probe (id serial PRIMARY KEY)")
        owner.execute("ALTER SEQUENCE sequence_rollback_probe_id_seq CYCLE")
        with pytest.raises(errors.RaiseException, match="revisión manual"):
            run_sql(owner, "integrated_sequence_repair.sql")
        owner.execute("ROLLBACK")
        assert owner.execute("SELECT last_value,is_called FROM documentos_base_id_documento_seq").fetchone() == {
            "last_value": 6, "is_called": True,
        }
        owner.execute("DROP TABLE sequence_rollback_probe")

        for _ in range(2):
            with owner.transaction():
                run_sql(owner, "phase1_postgres.sql")
                run_sql(owner, "phase2b_postgres.sql")
            run_sql(owner, "phase2c_postgres.sql")
            run_sql(owner, "integrated_order_integrity.sql")
            run_sql(owner, "integrated_sequence_repair.sql")
        assert owner.execute("SELECT count(*) AS n FROM schema_migrations").fetchone()["n"] == 2
        assert owner.execute("SELECT last_value,is_called FROM documentos_base_id_documento_seq").fetchone() == {
            "last_value": 19, "is_called": False,
        }
        assert owner.execute("SELECT last_value,is_called FROM categorias_reclamo_id_categoria_seq").fetchone() == {
            "last_value": 500, "is_called": False,
        }
        assert owner.execute("SELECT id_pedido FROM reclamos WHERE codigo_reclamo='CLAIM-LAB'").fetchone()["id_pedido"] is None
        with pytest.raises(errors.ForeignKeyViolation, match="reclamos_pedido_cliente_fk"):
            owner.execute("UPDATE reclamos SET id_pedido = (SELECT id_pedido FROM pedidos WHERE codigo_pedido='ORDER-LAB')")

        catalog = ROOT / "data/documentos_academicos.json"
        mixed = tmp_path / "mixed.json"
        records = json.loads(catalog.read_text(encoding="utf-8"))
        mixed.write_text(json.dumps([records[0], {**records[1], "version": "invalid"}]), encoding="utf-8")
        assert {r["status"] for r in import_documents(None, mixed, postgres_dsn=hardening_postgres, append_fragments=True)} == {
            "blocked", "rejected",
        }
        assert not owner.execute("SELECT to_regclass('documentos_importados') AS rel").fetchone()["rel"]
        assert {r["status"] for r in import_documents(None, catalog, postgres_dsn=hardening_postgres, dry_run=True,
                                                       append_fragments=True)} == {"created"}
        assert {r["status"] for r in import_documents(None, catalog, postgres_dsn=hardening_postgres,
                                                       append_fragments=True)} == {"created"}
        assert {r["status"] for r in import_documents(None, catalog, postgres_dsn=hardening_postgres,
                                                       append_fragments=True)} == {"skipped"}
        assert owner.execute("SELECT count(*) AS n FROM documentos_base").fetchone()["n"] == 60
        assert owner.execute("""
            SELECT count(*) AS n FROM documentos_importados d
            WHERE EXISTS (SELECT 1 FROM fragmentos_documento f WHERE f.id_documento=d.id_documento)
        """).fetchone()["n"] == 42
        assert owner.execute("SELECT count(*) AS n FROM rag_embeddings").fetchone()["n"] == len(snapshots["rag_embeddings"])
        for table, key in (("documentos_base", "id_documento"), ("fragmentos_documento", "id_fragmento"),
                           ("rag_embeddings", "id_embedding")):
            rows = owner.execute(sql.SQL("SELECT {} AS id, to_jsonb(t) AS row FROM {} t WHERE {} = ANY(%s)").format(
                sql.Identifier(key), sql.Identifier(table), sql.Identifier(key)), (list(snapshots[table]),)).fetchall()
            assert {row["id"]: row["row"] for row in rows} == snapshots[table]


def test_client_cannot_read_foreign_order_claim_or_upgrade_role(restricted_postgres):
    from backend.main import app
    with TestClient(app) as api:
        owner = auth(api)
        order = api.get("/api/orders", headers=owner).json()["items"][0]
        claim = new_claim(api, False)["claim"]
        signup = api.post("/api/auth/register", json={
            "name": "Cliente aislado", "email": "isolated@example.com", "password": "isolated-demo-password",
            "role": "ADMIN",
        })
        assert signup.status_code == 201, signup.text
        assert signup.json()["user"]["role"] == "CLIENT"
        token = api.post("/api/auth/login", json={
            "email": "isolated@example.com", "password": "isolated-demo-password",
        }).json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        assert api.get(f"/api/orders/{order['id']}", headers=headers).status_code == 403
        assert api.get(f"/api/claims/{claim['id']}", headers=headers).status_code in {403, 404}
        assert api.get(f"/api/claims/{claim['id']}/messages", headers=headers).status_code in {403, 404}
        user_id = signup.json()["user"]["id"]
        escalation = api.patch(f"/api/operations/users/{user_id}", headers=headers, json={
            "role": "ADMIN", "active": True, "reason": "Intento de escalamiento",
            "request_id": "self-escalation-security-probe",
        })
        assert escalation.status_code == 403
        assert api.get("/api/config", headers=auth(api, "AGENT")).status_code == 403
        assert api.get("/api/config", headers=auth(api, "ADMIN")).status_code == 200
