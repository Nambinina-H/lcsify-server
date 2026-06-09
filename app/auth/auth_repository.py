from sqlalchemy import func, select

from app.database.database_session import SessionLocal
from app.database.models import User


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


def create(email: str, password_hash: str, name: str, role: str):
    with SessionLocal() as session:
        user = User(
            email=email, password_hash=password_hash, name=name, role=role
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user
