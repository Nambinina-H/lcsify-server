from fastapi import APIRouter, Depends, HTTPException

from app.auth import auth_service
from app.auth.schemas import (
    LoginIn,
    RefreshIn,
    TokenOut,
    UserOut,
    VerifyPasswordIn,
)
from app.security.security import get_current_user

router = APIRouter()


@router.post("/api/auth/login", response_model=TokenOut)
def login(payload: LoginIn):
    return auth_service.login(payload.email, payload.password)


@router.post("/api/auth/refresh", response_model=TokenOut)
def refresh(payload: RefreshIn):
    return auth_service.refresh(payload.refresh_token)


@router.get("/api/auth/me", response_model=UserOut)
def me(user: dict = Depends(get_current_user)):
    return auth_service.me(user["id"])


@router.post("/api/auth/verify-password")
def verify_password(payload: VerifyPasswordIn, user: dict = Depends(get_current_user)):
    """Re-confirme le mot de passe du compte connecté (action sensible)."""
    if not auth_service.check_password(user["id"], payload.password):
        raise HTTPException(status_code=401, detail="Mot de passe incorrect")
    return {"ok": True}
