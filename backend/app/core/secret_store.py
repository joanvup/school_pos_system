import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

PREFIX = "enc:v1:"


def _fernet() -> Fernet:
    # Acepta una cadena arbitraria larga y la deriva a una clave Fernet válida.
    material = settings.SETTINGS_ENCRYPTION_KEY or settings.SECRET_KEY
    digest = hashlib.sha256(material.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def is_encrypted(value: str) -> bool:
    return isinstance(value, str) and value.startswith(PREFIX)


def encrypt_secret(value: str) -> str:
    if value is None:
        return ""
    value = str(value)
    if not value or is_encrypted(value):
        return value
    token = _fernet().encrypt(value.encode("utf-8")).decode("ascii")
    return f"{PREFIX}{token}"


def decrypt_secret(value: str) -> str:
    if not value:
        return ""
    if not is_encrypted(value):
        return str(value)
    try:
        token = value[len(PREFIX):].encode("ascii")
        return _fernet().decrypt(token).decode("utf-8")
    except (InvalidToken, ValueError) as exc:
        raise ValueError("No se pudo descifrar el secreto configurado") from exc
