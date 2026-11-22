import os
from unittest.mock import patch

import pytest

from scripts.demo_rag import configure_demo_environment


def test_demo_keeps_openai_off_and_database_isolated_by_default(monkeypatch, tmp_path):
    with patch.dict(os.environ):
        monkeypatch.setenv("DATABASE_URL", "postgresql://unused:unused@production.invalid/postgres")
        monkeypatch.setenv("OPENAI_API_KEY", "inherited-key")
        configure_demo_environment(15173, env_file=tmp_path / "missing.env")

        assert os.environ["DATABASE_URL"] == ""
        assert os.environ["DB_PROVIDER"] == "sqlite"
        assert os.environ["OPENAI_API_KEY"] == ""
        assert os.environ["USE_OPENAI_EMBEDDINGS"] == "false"
        assert os.environ["PYTHON_DOTENV_DISABLED"] == "1"


def test_demo_reads_only_openai_key_when_explicitly_enabled(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        'DATABASE_URL=postgresql://unused:unused@production.invalid/postgres\n'
        'AUTH_SECRET=must-not-be-loaded\n'
        'OPENAI_API_KEY="test-only-key"\n',
        encoding="utf-8",
    )
    with patch.dict(os.environ):
        monkeypatch.delenv("AUTH_SECRET", raising=False)
        configure_demo_environment(15173, enable_openai=True, env_file=env_file)

        assert os.environ["OPENAI_API_KEY"] == "test-only-key"
        assert os.environ["DATABASE_URL"] == ""
        assert os.environ["AUTH_SECRET"] != "must-not-be-loaded"
        assert os.environ["USE_OPENAI_EMBEDDINGS"] == "false"


def test_demo_requires_key_for_explicit_openai_mode(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("DATABASE_URL=postgresql://unused:unused@production.invalid/postgres\n",
                        encoding="utf-8")
    with pytest.raises(RuntimeError, match="Configura OPENAI_API_KEY"):
        configure_demo_environment(15173, enable_openai=True, env_file=env_file)
