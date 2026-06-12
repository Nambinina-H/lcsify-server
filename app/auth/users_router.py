from fastapi import APIRouter, Depends

from app.auth import users_service
from app.auth.schemas import PasswordIn, UserAdminOut, UserCreateIn, UserUpdateIn
from app.security.scopes import require_scope

router = APIRouter(prefix="/api/admin/users")

# Lecture : admin ou users:view. Ecritures : admin ou users:manage.
# (Le service applique en plus les garde-fous anti-escalade.)
_view = require_scope("users", "view")
_manage = require_scope("users", "manage")


@router.get("", response_model=list[UserAdminOut])
def list_users(_=Depends(_view)):
    return users_service.list_users()


@router.post("", response_model=UserAdminOut)
def create_user(payload: UserCreateIn, user=Depends(_manage)):
    return users_service.create_user(payload, user)


@router.patch("/{user_id}", response_model=UserAdminOut)
def update_user(user_id: int, payload: UserUpdateIn, user=Depends(_manage)):
    return users_service.update_user(user_id, payload, user)


@router.post("/{user_id}/password")
def reset_password(user_id: int, payload: PasswordIn, user=Depends(_manage)):
    return users_service.reset_password(user_id, payload, user)


@router.delete("/{user_id}")
def delete_user(user_id: int, user=Depends(_manage)):
    return users_service.delete_user(user_id, user)
