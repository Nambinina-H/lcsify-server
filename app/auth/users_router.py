from fastapi import APIRouter, Depends

from app.auth import users_service
from app.auth.schemas import PasswordIn, UserAdminOut, UserCreateIn, UserUpdateIn
from app.security.security import require_admin

router = APIRouter(prefix="/api/admin/users")


@router.get("", response_model=list[UserAdminOut])
def list_users(_=Depends(require_admin)):
    return users_service.list_users()


@router.post("", response_model=UserAdminOut)
def create_user(payload: UserCreateIn, user=Depends(require_admin)):
    return users_service.create_user(payload, user)


@router.patch("/{user_id}", response_model=UserAdminOut)
def update_user(user_id: int, payload: UserUpdateIn, user=Depends(require_admin)):
    return users_service.update_user(user_id, payload, user)


@router.post("/{user_id}/password")
def reset_password(user_id: int, payload: PasswordIn, user=Depends(require_admin)):
    return users_service.reset_password(user_id, payload, user)


@router.delete("/{user_id}")
def delete_user(user_id: int, user=Depends(require_admin)):
    return users_service.delete_user(user_id, user)
