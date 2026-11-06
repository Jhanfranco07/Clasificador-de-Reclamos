import os
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
import pytest

from database import db_connection as db
from scripts.import_documents import local_test_dsn


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
