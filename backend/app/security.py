"""Хеширование паролей (scrypt из стандартной библиотеки) и JWT-токены."""

import base64
import hashlib
import hmac
import os
from datetime import UTC, datetime, timedelta

import jwt

from app.config import get_settings

_N, _R, _P = 2**14, 8, 1


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P)
    return "scrypt${}${}".format(
        base64.b64encode(salt).decode(), base64.b64encode(digest).decode()
    )


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt_b64, digest_b64 = stored.split("$")
        if scheme != "scrypt":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
    except ValueError:
        return False
    actual = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P)
    return hmac.compare_digest(actual, expected)


# Хеш-заглушка: проверяем пароль и для несуществующего email, чтобы ответ не выдавал,
# есть ли такой пользователь.
DUMMY_HASH = hash_password("dummy-password")


def create_access_token(user_id: int) -> str:
    settings = get_settings()
    expires = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode({"sub": str(user_id), "exp": expires}, settings.secret_key, algorithm="HS256")


def decode_access_token(token: str) -> int:
    """Возвращает id пользователя или бросает jwt.PyJWTError."""
    payload = jwt.decode(token, get_settings().secret_key, algorithms=["HS256"])
    return int(payload["sub"])
