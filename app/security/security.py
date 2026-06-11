import secrets

import jwt
from fastapi import Depends, Header, HTTPException

from app.common.enums import RoleEnum
from app.env.settings import AGENT_API_KEY
from app.security.jwt import ACCESS, decode_token


def check_agent_key(x_api_key: str = Header(None)):
    """Authentification des agents (cle API partagee, en-tete X-API-Key)."""
    if not x_api_key or not secrets.compare_digest(x_api_key, AGENT_API_KEY):
        raise HTTPException(status_code=401, detail="Cle API invalide")


def get_current_user(authorization: str = Header(None)) -> dict:
    """Authentification des managers (JWT, en-tete Authorization: Bearer ...).

    Renvoie le contenu du token : {id, role}. Leve 401 si absent/invalide.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authentification requise")
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Jeton invalide ou expire")
    if payload.get("type") != ACCESS:
        raise HTTPException(status_code=401, detail="Type de jeton invalide")
    return {"id": int(payload["sub"]), "role": payload.get("role")}


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """Reserve aux administrateurs (config agents, utilisateurs, suppression)."""
    if user.get("role") != RoleEnum.ADMIN.value:
        raise HTTPException(status_code=403, detail="Acces administrateur requis")
    return user


def require_manager(user: dict = Depends(get_current_user)) -> dict:
    """Admin OU Manager (ex. creation / assignation de projets)."""
    if user.get("role") not in (RoleEnum.ADMIN.value, RoleEnum.MANAGER.value):
        raise HTTPException(status_code=403, detail="Acces refuse")
    return user
