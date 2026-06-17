from __future__ import annotations

import base64
import hashlib
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from app.security import SECRET_KEY

TEXT_ENCRYPTION_PREFIX = "enc::"


def _build_fernet() -> Fernet:
    digest = hashlib.sha256(f"{SECRET_KEY}:interview-file-encryption".encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_file_in_place(path_value: str) -> None:
    file_path = Path(path_value)
    payload = file_path.read_bytes()
    encrypted = _build_fernet().encrypt(payload)
    file_path.write_bytes(encrypted)


def decrypt_file_bytes(path_value: str) -> bytes:
    file_path = Path(path_value)
    payload = file_path.read_bytes()
    try:
        return _build_fernet().decrypt(payload)
    except InvalidToken as exc:
        raise ValueError("Unable to decrypt interview file contents.") from exc


def is_text_encrypted(value: str | None) -> bool:
    return bool(value and value.startswith(TEXT_ENCRYPTION_PREFIX))


def encrypt_text_value(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if is_text_encrypted(normalized):
        return normalized
    encrypted = _build_fernet().encrypt(normalized.encode("utf-8")).decode("utf-8")
    return f"{TEXT_ENCRYPTION_PREFIX}{encrypted}"


def decrypt_text_value(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if not is_text_encrypted(normalized):
        return normalized
    token = normalized[len(TEXT_ENCRYPTION_PREFIX):]
    try:
        return _build_fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Unable to decrypt interview text contents.") from exc
