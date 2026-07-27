from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from backend.settings import get_log_encryption_key

ENCRYPTED_VALUE_PREFIX = "enc:v1:"

_cached_key: str | None = None
_cached_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _cached_key, _cached_fernet

    key = get_log_encryption_key()
    if _cached_fernet is not None and _cached_key == key:
        return _cached_fernet

    try:
        fernet = Fernet(key.encode("utf-8"))
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            "AGENTGUARD_LOG_ENCRYPTION_KEY must be a valid Fernet key. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())\""
        ) from exc

    _cached_key = key
    _cached_fernet = fernet
    return fernet


def is_encrypted_text(value: str | None) -> bool:
    return isinstance(value, str) and value.startswith(ENCRYPTED_VALUE_PREFIX)


def encrypt_text(value: str | None) -> str | None:
    if value is None:
        return None
    token = _get_fernet().encrypt(value.encode("utf-8")).decode("utf-8")
    return f"{ENCRYPTED_VALUE_PREFIX}{token}"


def decrypt_text(value: str | None) -> str | None:
    if value is None or not is_encrypted_text(value):
        return value

    token = value[len(ENCRYPTED_VALUE_PREFIX) :].encode("utf-8")
    try:
        return _get_fernet().decrypt(token).decode("utf-8")
    except InvalidToken as exc:
        raise RuntimeError("Unable to decrypt stored log value with AGENTGUARD_LOG_ENCRYPTION_KEY") from exc


def encrypt_float(value: float | int | None) -> str | None:
    if value is None:
        return None
    return encrypt_text(str(float(value)))


def decrypt_float(value: float | int | str | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, (float, int)):
        return float(value)
    decrypted = decrypt_text(value)
    if decrypted is None:
        return None
    return float(decrypted)


def decrypt_row_fields(row: dict, fields: tuple[str, ...]) -> dict:
    decrypted = dict(row)
    for field in fields:
        if field in decrypted:
            decrypted[field] = decrypt_text(decrypted[field])
    return decrypted


def decrypt_row_float_fields(row: dict, fields: tuple[str, ...]) -> dict:
    decrypted = dict(row)
    for field in fields:
        if field in decrypted:
            decrypted[field] = decrypt_float(decrypted[field])
    return decrypted
