from pathlib import Path
import os

import pytest

from scripts.smartclaim_backup import (
    BackupError, _read_env, _source_environment, decrypt_dpapi, encrypt_dpapi,
)


def test_read_env_and_reject_other_project(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATABASE_URL='" + "postgresql://" + "postgres.other:" + "dummy" +
        "@pooler.example.test:5432/postgres'\n",
        encoding="utf-8",
    )
    assert _read_env(env_file)["DATABASE_URL"].startswith("postgresql://")
    with pytest.raises(BackupError, match="Project ID"):
        _source_environment(env_file, "fydoupwykkshtpongcih")


@pytest.mark.skipif(os.name != "nt", reason="DPAPI pertenece a Windows")
def test_dpapi_roundtrip_and_tamper_detection(tmp_path):
    source = tmp_path / "source.dump"
    encrypted = tmp_path / "source.dump.dpapi"
    restored = tmp_path / "restored.dump"
    payload = (b"smartclaim-backup-test" * 70000) + b"end"
    source.write_bytes(payload)
    encrypt_dpapi(source, encrypted)
    decrypt_dpapi(encrypted, restored)
    assert restored.read_bytes() == payload

    broken = bytearray(encrypted.read_bytes())
    broken[-8] ^= 1
    corrupted = tmp_path / "corrupted.dpapi"
    corrupted.write_bytes(broken)
    with pytest.raises((OSError, BackupError)):
        decrypt_dpapi(corrupted, tmp_path / "must-not-restore.dump")
