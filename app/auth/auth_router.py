from fastapi import APIRouter, Depends

from app.auth import auth_service
from app.auth.schemas import LoginIn, RefreshIn, TokenOut, UserOut
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
