from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.audit import audit_service
from app.auth import auth_repository
from app.auth.schemas import PasswordIn, UserCreateIn, UserUpdateIn
from app.common.enums import RoleEnum
from app.security.jwt import hash_password

_ROLES = {RoleEnum.ADMIN.value, RoleEnum.MANAGER.value}
_ADMIN = RoleEnum.ADMIN.value


def _check_role(role: str):
    if role not in _ROLES:
        raise HTTPException(status_code=422, detail="Role invalide")


def list_users():
    return auth_repository.list_all()


def create_user(payload: UserCreateIn, actor: dict):
    _check_role(payload.role)
    if auth_repository.get_by_email(payload.email):
        raise HTTPException(status_code=409, detail="Cet email est deja utilise")
    try:
        user = auth_repository.create(
            email=payload.email,
            password_hash=hash_password(payload.password),
            name=payload.name,
            role=payload.role,
        )
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Cet email est deja utilise")
    audit_service.log_event(
        actor,
        "user.create",
        f"Compte créé : {payload.name} ({payload.email}) — {payload.role}",
    )
    return auth_repository.get_dict(user.id)


def update_user(user_id: int, payload: UserUpdateIn, actor: dict):
    current = auth_repository.get_dict(user_id)
    if current is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    if payload.role is not None:
        _check_role(payload.role)

    new_role = payload.role if payload.role is not None else current["role"]
    new_active = (
        payload.is_active if payload.is_active is not None else current["is_active"]
    )

    # Garde-fou : on ne se verrouille pas soi-meme.
    if user_id == actor["id"]:
        if new_role != _ADMIN:
            raise HTTPException(
                status_code=400, detail="Vous ne pouvez pas retirer votre propre role admin"
            )
        if not new_active:
            raise HTTPException(
                status_code=400, detail="Vous ne pouvez pas desactiver votre propre compte"
            )

    # Garde-fou : toujours au moins un admin actif.
    loses_admin = current["role"] == _ADMIN and (new_role != _ADMIN or not new_active)
    if loses_admin and auth_repository.count_active_admins() <= 1:
        raise HTTPException(
            status_code=400, detail="Au moins un administrateur actif est requis"
        )

    updated = auth_repository.update_fields(
        user_id, name=payload.name, role=payload.role, is_active=payload.is_active
    )
    audit_service.log_event(
        actor,
        "user.update",
        f"Compte modifié : {updated['name']} — {updated['role']}"
        + ("" if updated["is_active"] else " (désactivé)"),
    )
    return updated


def reset_password(user_id: int, payload: PasswordIn, actor: dict):
    current = auth_repository.get_dict(user_id)
    if current is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    auth_repository.set_password(user_id, hash_password(payload.password))
    audit_service.log_event(
        actor, "user.password", f"Mot de passe réinitialisé : {current['name']}"
    )
    return {"status": "ok"}


def delete_user(user_id: int, actor: dict):
    current = auth_repository.get_dict(user_id)
    if current is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    if user_id == actor["id"]:
        raise HTTPException(
            status_code=400, detail="Vous ne pouvez pas supprimer votre propre compte"
        )
    # Garde-fou : ne pas supprimer le dernier administrateur actif.
    if (
        current["role"] == _ADMIN
        and current["is_active"]
        and auth_repository.count_active_admins() <= 1
    ):
        raise HTTPException(
            status_code=400, detail="Au moins un administrateur actif est requis"
        )
    auth_repository.delete(user_id)
    audit_service.log_event(
        actor,
        "user.delete",
        f"Compte supprimé : {current['name']} ({current['email']})",
    )
    return {"status": "ok"}
