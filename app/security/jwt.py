"""Outils JWT + hachage de mot de passe (bcrypt) pour l'auth des managers."""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.env.settings import (
    JWT_ACCESS_TTL_MIN,
    JWT_REFRESH_TTL_DAYS,
    JWT_SECRET,
)

_ALGO = "HS256"
ACCESS = "access"
REFRESH = "refresh"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except (ValueError, TypeError):
        return False


def _create_token(user_id: int, role: str, kind: str, ttl: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": kind,
        "iat": now,
        "exp": now + ttl,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=_ALGO)


def create_access_token(user_id: int, role: str) -> str:
    return _create_token(user_id, role, ACCESS, timedelta(minutes=JWT_ACCESS_TTL_MIN))


def create_refresh_token(user_id: int, role: str) -> str:
    return _create_token(user_id, role, REFRESH, timedelta(days=JWT_REFRESH_TTL_DAYS))


def decode_token(token: str) -> dict:
    """Decode + valide la signature/expiration. Leve jwt.PyJWTError si invalide."""
    return jwt.decode(token, JWT_SECRET, algorithms=[_ALGO])
