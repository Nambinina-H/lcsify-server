import json

from sqlalchemy import func, select

from app.common.enums import RoleEnum
from app.database.database_session import SessionLocal
from app.database.models import User
from app.security.scopes import clean_scopes, parse_scopes

_ADMIN = RoleEnum.ADMIN.value
_UNSET = object()  # sentinelle : champ non fourni (vs liste vide qui efface)


def _to_dict(u: User) -> dict:
    return {
        "id": u.id,
        "email": u.email,
        "name": u.name,
        "role": u.role,
        "scopes": parse_scopes(u.scopes),
        "is_active": u.is_active,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


def get_by_email(email: str):
    with SessionLocal() as session:
        return session.execute(
            select(User).where(func.lower(User.email) == email.lower())
        ).scalar_one_or_none()


def get_by_id(user_id: int):
    with SessionLocal() as session:
        return session.get(User, user_id)


def count_users() -> int:
    with SessionLocal() as session:
        return session.execute(select(func.count()).select_from(User)).scalar() or 0


def create(email: str, password_hash: str, name: str, role: str, scopes=None):
    with SessionLocal() as session:
        user = User(
            email=email,
            password_hash=password_hash,
            name=name,
            role=role,
            scopes=json.dumps(clean_scopes(scopes)) if scopes else None,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


# --- Gestion des utilisateurs (admin) ---------------------------------------


def list_all() -> list[dict]:
    with SessionLocal() as session:
        rows = session.execute(select(User).order_by(User.id)).scalars().all()
        return [_to_dict(u) for u in rows]


def get_dict(user_id: int) -> dict | None:
    with SessionLocal() as session:
        user = session.get(User, user_id)
        return _to_dict(user) if user else None


def count_active_admins() -> int:
    with SessionLocal() as session:
        return session.execute(
            select(func.count())
            .select_from(User)
            .where(User.role == _ADMIN, User.is_active.is_(True))
        ).scalar() or 0


def update_fields(user_id: int, name=None, role=None, is_active=None, scopes=_UNSET):
    with SessionLocal() as session:
        user = session.get(User, user_id)
        if user is None:
            return None
        if name is not None:
            user.name = name
        if role is not None:
            user.role = role
        if is_active is not None:
            user.is_active = is_active
        if scopes is not _UNSET:  # liste (meme vide) -> on remplace
            user.scopes = json.dumps(clean_scopes(scopes)) if scopes else None
        session.commit()
        session.refresh(user)
        return _to_dict(user)


def set_password(user_id: int, password_hash: str) -> bool:
    with SessionLocal() as session:
        user = session.get(User, user_id)
        if user is None:
            return False
        user.password_hash = password_hash
        session.commit()
        return True


def delete(user_id: int) -> bool:
    with SessionLocal() as session:
        user = session.get(User, user_id)
        if user is None:
            return False
        session.delete(user)
        session.commit()
        return True
