"""All tests are offline and isolated from workspace and production persistence."""
from pathlib import Path
import shutil
from contextlib import contextmanager
from collections import Counter
import socket
import threading
import sqlite3
import tempfile
import os

import pytest

class ExternalAccessBlocked(AssertionError):
    pass


class ExternalGuard:
    def __init__(self):
        self.pending = []
        self.blocked = Counter()

    def block(self, kind):
        def forbidden(*args, **kwargs):
            self.pending.append(kind)
            self.blocked[kind] += 1
            raise ExternalAccessBlocked("External access blocked: " + kind)
        return forbidden

    @contextmanager
    def expect_blocked(self, kind):
        """Allow only a deliberate guard self-test; still never perform external I/O."""
        before = len(self.pending)
        with pytest.raises(ExternalAccessBlocked):
            yield
        assert self.pending[before:] == [kind]
        del self.pending[before:]


_guard = ExternalGuard()
_isolation = pytest.MonkeyPatch()
_child_python = None


def pytest_configure(config):
    global _child_python
    # Before collection/imports. Changes are process-local and restored on exit.
    for key, value in {
        "SMARTCLAIM_BOOTSTRAP_DEMO": "1", "PYTHON_DOTENV_DISABLED": "1", "APP_ENV": "development", "DB_PROVIDER": "sqlite",
        "DATABASE_URL": "", "OPENAI_API_KEY": "", "USE_OPENAI_EMBEDDINGS": "false",
        "ENABLE_PGVECTOR_RAG": "false", "AUTH_SECRET": "isolated-tests-secret-never-used-in-production",
    }.items():
        _isolation.setenv(key, value)

    original_connect_sqlite = sqlite3.connect
    temporary_root = Path(tempfile.gettempdir()).resolve()

    def connect_temporary_sqlite(database, *args, **kwargs):
        connection = original_connect_sqlite(database, *args, **kwargs)
        name = str(database)
        if name != ":memory:" and not name.startswith("file:") and Path(name).resolve().is_relative_to(temporary_root):
            # Disposable tests retain SQL transactions and file persistence, but do
            # not measure power-loss durability or wait for every physical fsync.
            connection.execute("PRAGMA synchronous=OFF")
        return connection

    _isolation.setattr(sqlite3, "connect", connect_temporary_sqlite)
    # The existing reconciliation tests launch stdlib-only Python CLI processes.
    # Apply the same disposable-file policy there without changing those CLIs.
    _child_python = tempfile.TemporaryDirectory(prefix="smartclaim-test-python-", ignore_cleanup_errors=True)
    bootstrap = Path(_child_python.name) / "sitecustomize.py"
    bootstrap.write_text('''import os
import sqlite3
import tempfile
from pathlib import Path

if os.getenv("SMARTCLAIM_DISPOSABLE_SQLITE") == "1":
    original_connect = sqlite3.connect
    temporary_root = Path(tempfile.gettempdir()).resolve()
    def connect(database, *args, **kwargs):
        connection = original_connect(database, *args, **kwargs)
        name = str(database)
        if name != ":memory:" and not name.startswith("file:") and Path(name).resolve().is_relative_to(temporary_root):
            connection.execute("PRAGMA synchronous=OFF")
        return connection
    sqlite3.connect = connect
''', encoding="utf-8")
    _isolation.setenv("SMARTCLAIM_DISPOSABLE_SQLITE", "1")
    _isolation.setenv("PYTHONPATH", os.pathsep.join(filter(None, [_child_python.name, os.getenv("PYTHONPATH", "")])))

    import openai
    import psycopg
    import httpx
    for name in ("OpenAI", "AsyncOpenAI", "Client", "AsyncClient", "AzureOpenAI", "AsyncAzureOpenAI"):
        _isolation.setattr(openai, name, _guard.block("model_client"))
    _isolation.setattr(psycopg, "connect", _guard.block("postgres"))
    _isolation.setattr(psycopg.Connection, "connect", _guard.block("postgres"))
    _isolation.setattr(psycopg.AsyncConnection, "connect", _guard.block("postgres"))
    _isolation.setattr(httpx.HTTPTransport, "handle_request", _guard.block("http"))
    _isolation.setattr(httpx.AsyncHTTPTransport, "handle_async_request", _guard.block("http_async"))

    # Windows asyncio uses a loopback socketpair internally. Allow only that
    # synchronous internal operation, never arbitrary loopback or remote sockets.
    original_pair, original_connect = socket.socketpair, socket.socket.connect
    local = threading.local()

    def socketpair(*args, **kwargs):
        local.in_pair = True
        try:
            return original_pair(*args, **kwargs)
        finally:
            local.in_pair = False

    def connect(sock, address):
        if getattr(local, "in_pair", False) and address[0] in {"127.0.0.1", "::1"}:
            return original_connect(sock, address)
        return _guard.block("socket")()

    _isolation.setattr(socket, "socketpair", socketpair)
    _isolation.setattr(socket.socket, "connect", connect)
    _isolation.setattr(socket.socket, "connect_ex", _guard.block("socket"))
    _isolation.setattr(socket, "getaddrinfo", _guard.block("dns"))


def pytest_unconfigure(config):
    _isolation.undo()
    if _child_python:
        temporary_directory = Path(_child_python.name).resolve()
        assert temporary_directory.is_relative_to(Path(tempfile.gettempdir()).resolve())
        _child_python.cleanup()


def pytest_sessionfinish(session, exitstatus):
    if _guard.pending:
        session.exitstatus = 1


def pytest_terminal_summary(terminalreporter):
    terminalreporter.write_line("Offline guard: unexpected attempts=" + str(len(_guard.pending))
                                + "; blocked self-test probes=" + str(sum(_guard.blocked.values())))
    terminalreporter.write_line("Disposable SQLite uses synchronous=OFF; physical crash durability is outside test scope.")


@pytest.fixture
def external_guard():
    return _guard


@pytest.fixture(autouse=True)
def isolated_offline_environment(monkeypatch, tmp_path):
    import database.db_connection as db
    import modules.rag_engine as rag
    import modules.openai_embeddings as embeddings
    import modules.classifier as classifier
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "isolated.db")
    vector_dir = tmp_path / "vector_store"
    monkeypatch.setattr(rag, "VECTOR_DIR", vector_dir)
    monkeypatch.setattr(rag, "VECTORIZER_PATH", vector_dir / "vectorizer.joblib")
    monkeypatch.setattr(rag, "MATRIX_PATH", vector_dir / "matrix.joblib")
    monkeypatch.setattr(rag, "METADATA_PATH", vector_dir / "metadata.joblib")
    monkeypatch.setattr(embeddings, "INDEX_PATH", vector_dir / "embeddings.json")
    model = tmp_path / "classifier.joblib"
    shutil.copyfile(Path(classifier.MODEL_PATH), model)
    monkeypatch.setattr(classifier, "MODEL_PATH", model)
    yield
    assert not _guard.pending, "Unexpected external attempt (even if application caught it): " + repr(_guard.pending)
