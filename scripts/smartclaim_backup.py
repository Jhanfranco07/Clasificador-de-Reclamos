"""Backup cifrado y validación aislada de SmartClaim sobre PostgreSQL/Supabase.

El subcomando ``backup`` solo lee la base remota. El subcomando ``validate``
restaura el dump en un contenedor efímero sin salida a Internet, aplica las
migraciones locales y elimina tanto el contenedor como el dump descifrado.
"""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import getpass
import hashlib
import json
import os
from pathlib import Path
import shutil
import secrets
import socket
import struct
import subprocess
import sys
import tempfile
import time
from urllib.parse import unquote, urlsplit
import uuid


ROOT = Path(__file__).resolve().parents[1]
PROJECT_REF = "fydoupwykkshtpongcih"
POSTGRES_IMAGE = "public.ecr.aws/supabase/postgres:17.11.0.011"
MAGIC = b"SMARTCLAIM-DPAPI-1\n"
CHUNK_SIZE = 1024 * 1024
PRESERVED_TABLES = {
    "auth_users": "id_auth_user",
    "clientes": "id_cliente",
    "pedidos": "id_pedido",
    "reclamos": "id_reclamo",
    "documentos_base": "id_documento",
    "fragmentos_documento": "id_fragmento",
    "rag_embeddings": "id_embedding",
}
MIGRATIONS = (
    "phase1_postgres.sql",
    "phase2b_postgres.sql",
    "phase2c_postgres.sql",
    "integrated_order_integrity.sql",
    "integrated_sequence_repair.sql",
    "integrated_database_security.sql",
)


class BackupError(RuntimeError):
    pass


def _private_root() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        raise BackupError("LOCALAPPDATA no está definido.")
    return Path(base) / "SmartClaim-Privado" / "backups"


def _run(args, *, env=None, cwd=None, timeout=300, check=True, input_text=None):
    result = subprocess.run(
        [str(item) for item in args], cwd=cwd, env=env, text=True,
        input=input_text, capture_output=True, timeout=timeout,
    )
    if check and result.returncode:
        detail = (result.stderr or result.stdout or "Error sin detalle").strip()
        raise BackupError(f"Falló {Path(str(args[0])).name}: {detail[-1200:]}")
    return result


def _docker(*args, env=None, timeout=300, check=True):
    return _run(["docker", *args], env=env, timeout=timeout, check=check)


def _require_docker():
    if not shutil.which("docker"):
        raise BackupError("Docker no está instalado.")
    _docker("version", "--format", "{{.Server.Version}}", timeout=20)
    present = _docker("image", "inspect", POSTGRES_IMAGE, check=False, timeout=20)
    if present.returncode:
        raise BackupError(
            f"Falta la imagen local {POSTGRES_IMAGE}. Descárgala explícitamente antes de continuar."
        )


def _read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[name.strip()] = value
    return values


def _source_environment(env_file: Path, project_ref: str) -> dict[str, str]:
    raw = _read_env(env_file).get("DATABASE_URL", "").strip()
    parsed = urlsplit(raw)
    user = unquote(parsed.username or "")
    password = unquote(parsed.password or "")
    host = parsed.hostname or ""
    if parsed.scheme not in {"postgres", "postgresql"} or not all((user, password, host)):
        raise BackupError("DATABASE_URL no contiene una conexión PostgreSQL completa.")
    if project_ref not in host and project_ref not in user:
        raise BackupError("La conexión no corresponde al Project ID autorizado.")
    child = os.environ.copy()
    child.update({
        "PGHOST": host,
        "PGPORT": str(parsed.port or 5432),
        "PGDATABASE": parsed.path.lstrip("/") or "postgres",
        "PGUSER": user,
        "PGPASSWORD": password,
        "PGSSLMODE": "require",
        "PGCONNECT_TIMEOUT": "20",
        "PGOPTIONS": "-c default_transaction_read_only=on -c statement_timeout=0",
    })
    return child


def _restrict_acl(path: Path):
    if os.name != "nt":
        path.chmod(0o700)
        return
    user = getpass.getuser()
    result = _run([
        "icacls", path, "/inheritance:r", "/grant:r",
        f"{user}:(OI)(CI)F", "SYSTEM:(OI)(CI)F",
    ], check=False, timeout=30)
    if result.returncode:
        raise BackupError("No se pudieron restringir los permisos del directorio privado.")


class _Blob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _dpapi(data: bytes, *, protect: bool) -> bytes:
    if os.name != "nt":
        raise BackupError("El cifrado DPAPI solo está disponible en Windows.")
    buffer = ctypes.create_string_buffer(data)
    incoming = _Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)))
    outgoing = _Blob()
    crypt32 = ctypes.windll.crypt32
    function = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
    if protect:
        ok = function(ctypes.byref(incoming), "SmartClaim backup", None, None, None, 1,
                      ctypes.byref(outgoing))
    else:
        ok = function(ctypes.byref(incoming), None, None, None, None, 1,
                      ctypes.byref(outgoing))
    if not ok:
        raise ctypes.WinError()
    try:
        return ctypes.string_at(outgoing.pbData, outgoing.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(outgoing.pbData)


def encrypt_dpapi(source: Path, destination: Path):
    with source.open("rb") as reader, destination.open("xb") as writer:
        writer.write(MAGIC)
        while chunk := reader.read(CHUNK_SIZE):
            sealed = _dpapi(chunk, protect=True)
            writer.write(struct.pack(">I", len(sealed)))
            writer.write(sealed)
        writer.write(struct.pack(">I", 0))


def decrypt_dpapi(source: Path, destination: Path):
    with source.open("rb") as reader, destination.open("xb") as writer:
        if reader.read(len(MAGIC)) != MAGIC:
            raise BackupError("El archivo no tiene el formato cifrado de SmartClaim.")
        while True:
            length_raw = reader.read(4)
            if len(length_raw) != 4:
                raise BackupError("El respaldo cifrado está truncado.")
            length = struct.unpack(">I", length_raw)[0]
            if length == 0:
                if reader.read(1):
                    raise BackupError("El respaldo contiene bytes inesperados al final.")
                return
            sealed = reader.read(length)
            if len(sealed) != length:
                raise BackupError("El respaldo cifrado está truncado.")
            writer.write(_dpapi(sealed, protect=False))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_query(env, sql: str):
    command = [
        "run", "--rm",
        "-e", "PGHOST", "-e", "PGPORT", "-e", "PGDATABASE", "-e", "PGUSER",
        "-e", "PGPASSWORD", "-e", "PGSSLMODE", "-e", "PGCONNECT_TIMEOUT", "-e", "PGOPTIONS",
        POSTGRES_IMAGE, "psql", "-X", "-q", "-A", "-t", "-v", "ON_ERROR_STOP=1", "-c", sql,
    ]
    result = _docker(*command, env=env, timeout=60)
    return json.loads(result.stdout.strip())


def backup(args) -> int:
    _require_docker()
    source_env = _source_environment(args.source_env_file.resolve(), args.project_ref)
    metadata = _source_query(source_env, """
        SELECT json_build_object(
            'server_version', current_setting('server_version'),
            'database_bytes', pg_database_size(current_database()),
            'extensions', COALESCE((
                SELECT json_agg(json_build_object('name', extname, 'version', extversion,
                    'schema', n.nspname) ORDER BY extname)
                FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace
            ), '[]'::json)
        );
    """)
    if not str(metadata["server_version"]).startswith("17."):
        raise BackupError("La versión productiva ya no coincide con el cliente PostgreSQL 17 preparado.")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = (args.output_dir or _private_root()) / f"smartclaim-{stamp}"
    output.mkdir(parents=True, exist_ok=False)
    _restrict_acl(output)
    plain = output / "smartclaim-public.dump"
    encrypted = output / "smartclaim-public.dump.dpapi"
    manifest_path = output / "manifest.json"
    mount = f"type=bind,source={output},target=/backup"
    try:
        command = [
            "run", "--rm",
            "-e", "PGHOST", "-e", "PGPORT", "-e", "PGDATABASE", "-e", "PGUSER",
            "-e", "PGPASSWORD", "-e", "PGSSLMODE", "-e", "PGCONNECT_TIMEOUT", "-e", "PGOPTIONS",
            "--mount", mount,
            POSTGRES_IMAGE, "pg_dump", "--format=custom", "--compress=9",
            "--schema=public", "--no-owner", "--no-acl", "--file=/backup/smartclaim-public.dump",
        ]
        _docker(*command, env=source_env, timeout=1800)
        if not plain.exists() or plain.stat().st_size == 0:
            raise BackupError("pg_dump no generó un archivo válido.")
        listing = _docker(
            "run", "--rm", "--mount", mount, POSTGRES_IMAGE,
            "pg_restore", "--list", "/backup/smartclaim-public.dump", timeout=180,
        )
        if "TABLE DATA public" not in listing.stdout:
            raise BackupError("El catálogo de pg_restore no contiene datos de tablas public.")
        plain_hash = _sha256(plain)
        encrypt_dpapi(plain, encrypted)
        encrypted_hash = _sha256(encrypted)
        manifest = {
            "format": "smartclaim-backup-v1",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "project_ref": args.project_ref,
            "scope": "public schema; no owner; no ACL",
            "source": metadata,
            "plain_sha256": plain_hash,
            "encrypted_sha256": encrypted_hash,
            "plain_bytes": plain.stat().st_size,
            "encrypted_bytes": encrypted.stat().st_size,
            "encryption": "Windows DPAPI, usuario actual y equipo actual",
            "restore_requirements": {
                "postgres_major": 17,
                "vector": next((item for item in metadata["extensions"] if item["name"] == "vector"), None),
            },
            "not_included": [
                "contraseñas de roles globales", "objetos binarios de Supabase Storage",
                "configuración Auth/SMTP/OAuth", "Edge Functions", "API keys/JWT secrets",
                "configuración de Realtime y plataforma",
            ],
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        if _sha256(encrypted) != encrypted_hash:
            raise BackupError("La verificación posterior del archivo cifrado falló.")
    finally:
        if plain.exists():
            plain.unlink()
    print(json.dumps({
        "status": "backup_ok", "backup": str(encrypted), "manifest": str(manifest_path),
        "sha256": encrypted_hash, "bytes": encrypted.stat().st_size,
    }, ensure_ascii=False))
    return 0


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _exec(container: str, *command, timeout=300, check=True):
    return _docker("exec", container, *command, timeout=timeout, check=check)


def _pg_exec(container: str, program: str, *command, timeout=300, check=True):
    return _exec(
        container, "sh", "-c", 'export PGPASSWORD="$POSTGRES_PASSWORD"; exec "$@"',
        "smartclaim-pg", program, "-h", "127.0.0.1", *command,
        timeout=timeout, check=check,
    )


def _psql(container: str, database: str, sql: str, *, timeout=300):
    return _pg_exec(container, "psql", "-U", "postgres", "-d", database, "-X", "-q", "-A", "-t",
                    "-v", "ON_ERROR_STOP=1", "-c", sql, timeout=timeout)


def _json_query(container: str, database: str, query: str):
    wrapped = f"SELECT COALESCE(json_agg(row_to_json(q)), '[]'::json) FROM ({query}) q"
    result = _psql(container, database, wrapped)
    return json.loads(result.stdout.strip() or "[]")


def _columns(container: str, database: str, table: str) -> list[str]:
    rows = _json_query(container, database, f"""
        SELECT column_name FROM information_schema.columns
        WHERE table_schema='public' AND table_name='{table}' ORDER BY ordinal_position
    """)
    return [row["column_name"] for row in rows]


def _quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _digest(container: str, database: str, table: str, columns: list[str], where="TRUE"):
    selected = ",".join(_quote(column) for column in columns)
    rows = _json_query(container, database, f"""
        SELECT count(*)::int AS count,
          md5(COALESCE(string_agg(md5(to_jsonb(x)::text), '' ORDER BY md5(to_jsonb(x)::text)), '')) AS hash
        FROM (SELECT {selected} FROM public.{_quote(table)} WHERE {where}) x
    """)
    return rows[0]


def _snapshot(container: str, database: str):
    result = {}
    for table, key in PRESERVED_TABLES.items():
        columns = _columns(container, database, table)
        maxima = _json_query(container, database,
                             f"SELECT max({_quote(key)}) AS max_id FROM public.{_quote(table)}")
        result[table] = {
            "key": key, "columns": columns, "max_id": maxima[0]["max_id"],
            **_digest(container, database, table, columns),
        }
    return result


def _migration(container: str, database: str, filename: str):
    _pg_exec(container, "psql", "-U", "postgres", "-d", database, "-X", "-q",
             "-v", "ON_ERROR_STOP=1", "-f", f"/repo/database/migrations/{filename}", timeout=600)


def _run_module(module: str, module_args: list[str], dsn: str, *, allow_failure=False):
    env = os.environ.copy()
    env.update({
        "SMARTCLAIM_TEST_PG_DSN": dsn, "DATABASE_URL": "", "OPENAI_API_KEY": "",
        "USE_OPENAI_EMBEDDINGS": "false", "MODEL_PROVIDER": "local",
        "PYTHON_DOTENV_DISABLED": "1",
    })
    result = _run([sys.executable, "-B", "-m", module, *module_args], env=env, cwd=ROOT,
                  timeout=600, check=not allow_failure)
    return result


def _latest_backup(directory: Path) -> Path:
    files = sorted(directory.glob("smartclaim-*/smartclaim-public.dump.dpapi"))
    if not files:
        raise BackupError("No hay respaldos SmartClaim en el directorio privado.")
    return files[-1]


def validate(args) -> int:
    _require_docker()
    backup_path = (args.backup or _latest_backup(_private_root())).resolve()
    manifest_path = backup_path.with_name("manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("format") != "smartclaim-backup-v1":
        raise BackupError("Manifest desconocido.")
    if _sha256(backup_path) != manifest.get("encrypted_sha256"):
        raise BackupError("El SHA-256 del respaldo cifrado no coincide.")

    run_id = uuid.uuid4().hex[:12]
    private = _private_root() / f"staging-{run_id}"
    private.mkdir(parents=True, exist_ok=False)
    _restrict_acl(private)
    plain = private / "smartclaim-public.dump"
    report_path = backup_path.parent / f"validation-{run_id}.json"
    container = f"smartclaim-staging-{run_id}"
    network = f"smartclaim-internal-{run_id}"
    port = _free_port()
    staging_password = secrets.token_urlsafe(32)
    staging_env = os.environ.copy()
    staging_env["POSTGRES_PASSWORD"] = staging_password
    report = {"status": "failed", "backup": str(backup_path), "started_at_utc": datetime.now(timezone.utc).isoformat()}
    try:
        decrypt_dpapi(backup_path, plain)
        if _sha256(plain) != manifest.get("plain_sha256"):
            raise BackupError("El dump descifrado no coincide con el SHA-256 original.")
        _docker("network", "create", network, timeout=60)
        dump_mount = f"type=bind,source={private},target=/backup,readonly"
        repo_mount = f"type=bind,source={ROOT},target=/repo,readonly"
        _docker(
            "run", "-d", "--name", container, "--network", network,
            "--tmpfs", "/var/lib/postgresql/data:rw,nosuid,size=2g",
            "-p", f"127.0.0.1:{port}:5432", "-e", "POSTGRES_PASSWORD",
            "--mount", dump_mount, "--mount", repo_mount, POSTGRES_IMAGE,
            env=staging_env, timeout=120,
        )
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            ready = _exec(container, "pg_isready", "-U", "postgres", "-d", "postgres",
                          timeout=10, check=False)
            if ready.returncode == 0:
                break
            time.sleep(2)
        else:
            logs = _docker("logs", "--tail", "80", container, check=False).stdout
            raise BackupError(f"PostgreSQL staging no inició: {logs[-1200:]}")

        source_db = "smartclaim_source"
        validation_db = "smartclaim_test_staging"
        rollback_db = "smartclaim_rollback"
        _psql(container, "postgres", f"CREATE DATABASE {source_db} TEMPLATE template0")
        listing = _exec(container, "pg_restore", "--list", "/backup/smartclaim-public.dump").stdout
        restore_list = private / "restore.list"
        restore_list.write_text(
            "\n".join(line for line in listing.splitlines() if " SCHEMA - public " not in line) + "\n",
            encoding="utf-8",
        )
        _psql(container, source_db, "DROP SCHEMA public CASCADE")
        _psql(container, source_db, "CREATE SCHEMA public; CREATE EXTENSION vector WITH SCHEMA public")
        _pg_exec(container, "pg_restore", "--exit-on-error", "--no-owner", "--no-acl",
                 "--use-list=/backup/restore.list", "-U", "postgres", "-d", source_db,
                 "/backup/smartclaim-public.dump", timeout=900)
        _psql(container, "postgres", f"CREATE DATABASE {validation_db} TEMPLATE {source_db}")

        before = _snapshot(container, source_db)
        validation_before = _snapshot(container, validation_db)
        if before != validation_before:
            raise BackupError("La copia de validación no coincide con la restauración inicial.")

        for _ in range(2):
            for filename in MIGRATIONS:
                _migration(container, validation_db, filename)

        preserved_after_sql = {}
        for table, item in before.items():
            current = _digest(container, validation_db, table, item["columns"])
            preserved_after_sql[table] = current
            if current != {"count": item["count"], "hash": item["hash"]}:
                raise BackupError(f"La migración SQL alteró filas históricas de {table}.")

        dsn = (f"host=127.0.0.1 hostaddr=127.0.0.1 port={port} dbname={validation_db} "
               f"user=postgres password={staging_password} sslmode=disable")
        plan_result = _run_module("scripts.plan_document_migration", [], dsn, allow_failure=True)
        plan = json.loads(plan_result.stdout)
        if plan.get("counts", {}).get("conflict"):
            raise BackupError("El plan documental detectó conflictos que requieren conciliación manual.")
        if plan.get("sequence_needs_review"):
            raise BackupError(
                "La secuencia documental aún requiere revisión después de la reparación "
                f"(max_id={plan.get('max_document_id')}, last_value={plan.get('document_sequence_last_value')})."
            )
        backfill_plan = json.loads(_run_module(
            "scripts.import_documents", ["--postgres-test", "--backfill-fragments", "--dry-run"], dsn
        ).stdout)
        _run_module("scripts.import_documents", ["--postgres-test", "--backfill-fragments"], dsn)
        backfill_repeat = json.loads(_run_module(
            "scripts.import_documents", ["--postgres-test", "--backfill-fragments", "--dry-run"], dsn
        ).stdout)
        catalog_dry = json.loads(_run_module(
            "scripts.import_documents", ["--postgres-test", "--append-fragments", "--dry-run"], dsn
        ).stdout)
        _run_module("scripts.import_documents", ["--postgres-test", "--append-fragments"], dsn)
        catalog_repeat = json.loads(_run_module(
            "scripts.import_documents", ["--postgres-test", "--append-fragments", "--dry-run"], dsn
        ).stdout)

        original_document_hashes = {}
        for table in ("documentos_base", "fragmentos_documento", "rag_embeddings"):
            item = before[table]
            where = f"{_quote(item['key'])} <= {int(item['max_id'] or 0)}"
            original_document_hashes[table] = _digest(
                container, validation_db, table, item["columns"], where=where
            )
            expected = {"count": item["count"], "hash": item["hash"]}
            if original_document_hashes[table] != expected:
                raise BackupError(f"No se conservaron las filas documentales históricas de {table}.")

        checks = _json_query(container, validation_db, """
            WITH open_orders AS (
              SELECT p.id_pedido,
                (SELECT count(*) FROM public.restaurantes r
                 WHERE lower(trim(r.nombre))=lower(trim(p.tienda_nombre))) AS candidates
              FROM public.pedidos p WHERE p.estado NOT IN ('DELIVERED','CANCELLED')
            ), claim_links AS (
              SELECT r.id_reclamo,
                (SELECT count(*) FROM public.pedidos p
                 WHERE p.codigo_pedido=r.codigo_pedido AND p.id_cliente=r.id_cliente) AS candidates
              FROM public.reclamos r
            )
            SELECT
              (SELECT count(*)::int FROM open_orders) AS open_orders,
              (SELECT count(*)::int FROM open_orders WHERE candidates=1) AS open_orders_unique_merchant,
              (SELECT count(*)::int FROM open_orders WHERE candidates<>1) AS open_orders_manual_review,
              (SELECT count(*)::int FROM claim_links WHERE candidates=1) AS claims_unique_order,
              (SELECT count(*)::int FROM claim_links WHERE candidates<>1) AS claims_manual_review,
              (SELECT count(*)::int FROM pg_constraint c JOIN pg_class t ON t.oid=c.conrelid
                 JOIN pg_namespace n ON n.oid=t.relnamespace
                 WHERE n.nspname='public' AND NOT c.convalidated) AS invalid_constraints,
              (SELECT count(*)::int FROM pg_class t JOIN pg_namespace n ON n.oid=t.relnamespace
                 WHERE n.nspname='public' AND t.relkind='r' AND (NOT t.relrowsecurity OR NOT t.relforcerowsecurity))
                 AS tables_without_forced_rls,
              (SELECT count(*)::int FROM pg_roles WHERE rolname='smartclaim_backend' AND rolcanlogin
                 AND NOT (rolsuper OR rolbypassrls OR rolcreaterole OR rolcreatedb OR rolreplication OR rolinherit))
                 AS limited_backend_roles
        """)[0]
        exposed = _json_query(container, validation_db, """
            SELECT count(*)::int AS exposed_table_role_pairs
            FROM (VALUES ('anon'),('authenticated'),('service_role')) roles(role_name)
            CROSS JOIN pg_class t JOIN pg_namespace n ON n.oid=t.relnamespace
            WHERE n.nspname='public' AND t.relkind='r'
              AND has_table_privilege(role_name, t.oid, 'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
        """)[0]
        _psql(container, validation_db, """
            DO $verify_sequences$
            DECLARE item record; maximum numeric; last_id numeric; called boolean;
            BEGIN
              FOR item IN
                SELECT tbl.oid::regclass AS relation, col.attname AS column_name,
                       seq.oid::regclass AS sequence
                FROM pg_depend dep
                JOIN pg_class seq ON seq.oid=dep.objid AND seq.relkind='S'
                JOIN pg_class tbl ON tbl.oid=dep.refobjid AND tbl.relkind IN ('r','p')
                JOIN pg_attribute col ON col.attrelid=tbl.oid AND col.attnum=dep.refobjsubid
                WHERE dep.classid='pg_class'::regclass AND dep.refclassid='pg_class'::regclass
                  AND dep.deptype IN ('a','i') AND tbl.relnamespace='public'::regnamespace
              LOOP
                EXECUTE format('SELECT max(%I) FROM %s', item.column_name, item.relation) INTO maximum;
                EXECUTE format('SELECT last_value,is_called FROM %s', item.sequence) INTO last_id,called;
                IF maximum IS NOT NULL AND last_id + called::int <= maximum THEN
                  RAISE EXCEPTION 'Secuencia no reparada: %', item.sequence;
                END IF;
              END LOOP;
            END $verify_sequences$;
        """)
        sequence_issues = {"sequence_issues": 0}
        if checks["invalid_constraints"] or checks["tables_without_forced_rls"]:
            raise BackupError("Persisten restricciones inválidas o tablas sin RLS forzado.")
        if checks["limited_backend_roles"] != 1 or exposed["exposed_table_role_pairs"]:
            raise BackupError("La validación de privilegios mínimos falló.")
        if sequence_issues["sequence_issues"]:
            raise BackupError("La comprobación de secuencias detectó inconsistencias.")

        import psycopg
        from psycopg import sql
        with psycopg.connect(dsn, autocommit=True) as staging_owner:
            staging_owner.execute(
                sql.SQL("ALTER ROLE smartclaim_backend PASSWORD {}").format(sql.Literal(staging_password))
            )
            staging_owner.execute("GRANT smartclaim_backend TO postgres")

        test_env = os.environ.copy()
        test_env.update({
            "SMARTCLAIM_TEST_PG_DSN": dsn,
            "SMARTCLAIM_TEST_SECURITY_PG": "1",
            "DATABASE_URL": "",
            "OPENAI_API_KEY": "",
            "USE_OPENAI_EMBEDDINGS": "false",
            "MODEL_PROVIDER": "local",
            "PYTHON_DOTENV_DISABLED": "1",
        })
        focused_tests = _run([
            sys.executable, "-B", "-m", "pytest", "-q",
            "tests/test_api_auth_orders.py::test_registration_cannot_claim_a_legacy_customer[postgres]",
            "tests/test_postgres_hardening.py",
        ], env=test_env, cwd=ROOT, timeout=900)
        pytest_summary = next(
            (line.strip() for line in reversed(focused_tests.stdout.splitlines()) if " passed" in line),
            "pruebas focalizadas aprobadas",
        )

        _psql(container, "postgres", f"CREATE DATABASE {rollback_db} TEMPLATE {source_db}")
        rollback_snapshot = _snapshot(container, rollback_db)
        if rollback_snapshot != before:
            raise BackupError("La restauración de rollback no reproduce la copia original.")

        after_counts = {table: _digest(container, validation_db, table, _columns(container, validation_db, table))["count"]
                        for table in PRESERVED_TABLES}
        report.update({
            "status": "validation_ok",
            "completed_at_utc": datetime.now(timezone.utc).isoformat(),
            "staging": "contenedor efímero PG17/pgvector, red dedicada, puerto solo loopback",
            "backup_integrity": True,
            "sql_migrations_applied_twice": list(MIGRATIONS),
            "preserved_counts_before": {key: value["count"] for key, value in before.items()},
            "counts_after": after_counts,
            "historic_rows_preserved": True,
            "rollback_verified": True,
            "document_plan": {"counts": plan.get("counts"), "sequence_needs_review": plan.get("sequence_needs_review")},
            "backfill": {"initial": backfill_plan, "repeat": backfill_repeat},
            "catalog": {
                "dry_statuses": sorted({item["status"] for item in catalog_dry["results"]}),
                "repeat_statuses": sorted({item["status"] for item in catalog_repeat["results"]}),
            },
            "data_checks": checks,
            "public_access": exposed,
            "sequence_checks": sequence_issues,
            "focused_postgres_tests": pytest_summary,
            "production_mutated": False,
        })
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({
            "status": report["status"], "report": str(report_path), "open_orders": checks["open_orders"],
            "historic_rows_preserved": True, "rollback_verified": True,
        }, ensure_ascii=False))
        return 0
    finally:
        if plain.exists():
            plain.unlink()
        _docker("rm", "-f", container, check=False, timeout=60)
        _docker("network", "rm", network, check=False, timeout=60)
        if private.exists():
            shutil.rmtree(private, ignore_errors=True)
        if report["status"] == "failed" and not report_path.exists():
            report["failed_at_utc"] = datetime.now(timezone.utc).isoformat()
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    create = commands.add_parser("backup", help="Genera, verifica y cifra el respaldo lógico.")
    create.add_argument("--source-env-file", type=Path, required=True,
                        help="Archivo privado que contiene DATABASE_URL; no se copia ni se muestra.")
    create.add_argument("--project-ref", default=PROJECT_REF)
    create.add_argument("--output-dir", type=Path)
    create.set_defaults(handler=backup)
    verify = commands.add_parser("validate", help="Restaura y valida en staging efímero.")
    verify.add_argument("--backup", type=Path, help="Respaldo DPAPI; por defecto usa el más reciente.")
    verify.set_defaults(handler=validate)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        return args.handler(args)
    except (BackupError, subprocess.TimeoutExpired, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
