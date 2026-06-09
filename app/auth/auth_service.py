import jwt
from fastapi import HTTPException

from app.auth import auth_repository
from app.common.enums import RoleEnum
from app.env.settings import settings
from app.logging_config import get_logger
from app.security.jwt import (
    REFRESH,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

logger = get_logger()


def _user_out(user) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
    }


def _tokens_for(user) -> dict:
    return {
        "access_token": create_access_token(user.id, user.role),
        "refresh_token": create_refresh_token(user.id, user.role),
        "token_type": "bearer",
        "user": _user_out(user),
    }


def login(email: str, password: str) -> dict:
    user = auth_repository.get_by_email(email)
    if user is None or not user.is_active or not verify_password(
        password, user.password_hash
    ):
        raise HTTPException(status_code=401, detail="Identifiants invalides")
    return _tokens_for(user)


def refresh(refresh_token: str) -> dict:
    try:
        payload = decode_token(refresh_token)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Jeton de rafraichissement invalide")
    if payload.get("type") != REFRESH:
        raise HTTPException(status_code=401, detail="Type de jeton invalide")
    user = auth_repository.get_by_id(int(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Compte introuvable ou desactive")
    return _tokens_for(user)


def me(user_id: int) -> dict:
    user = auth_repository.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Compte introuvable")
    return _user_out(user)


def ensure_admin():
    """Cree le compte admin initial s'il n'existe aucun utilisateur."""
    if auth_repository.count_users() > 0:
        return
    auth_repository.create(
        email=settings.admin_email,
        password_hash=hash_password(settings.admin_password),
        name=settings.admin_name,
        role=RoleEnum.ADMIN.value,
    )
    logger.info("Compte admin initial cree : %s", settings.admin_email)
