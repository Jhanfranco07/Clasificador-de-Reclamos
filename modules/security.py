from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return f"pbkdf2_sha256$120000${salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations, salt, digest = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        ).hex()
        return hmac.compare_digest(candidate, digest)
    except Exception:
        return False


def _secret() -> bytes:
    value = os.getenv("AUTH_SECRET", "smartclaim-dev-secret-change-me")
    return value.encode("utf-8")


def create_token(payload: dict[str, Any], expires_in: int = 60 * 60 * 12) -> str:
    body = dict(payload)
    body["exp"] = int(time.time()) + expires_in
    raw = json.dumps(body, separators=(",", ":"), sort_keys=True).encode("utf-8")
    encoded_payload = _b64encode(raw)
    signature = hmac.new(_secret(), encoded_payload.encode("ascii"), hashlib.sha256).digest()
    return f"{encoded_payload}.{_b64encode(signature)}"


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        encoded_payload, encoded_signature = token.split(".", 1)
        expected = hmac.new(_secret(), encoded_payload.encode("ascii"), hashlib.sha256).digest()
        if not hmac.compare_digest(_b64decode(encoded_signature), expected):
            return None
        payload = json.loads(_b64decode(encoded_payload).decode("utf-8"))
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        return payload
    except Exception:
        return None
