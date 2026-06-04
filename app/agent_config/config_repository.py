from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.database.database import engine
from app.database.database_session import SessionLocal
from app.database.models import AppSetting


def get_all():
    with SessionLocal() as session:
        rows = session.execute(select(AppSetting.key, AppSetting.value)).all()
    return {r.key: r.value for r in rows}


def set_many(items):
    ins = pg_insert if engine.dialect.name == "postgresql" else sqlite_insert
    with SessionLocal() as session:
        for key, value in items.items():
            stmt = ins(AppSetting).values(key=key, value=str(value))
            stmt = stmt.on_conflict_do_update(
                index_elements=["key"], set_={"value": str(value)}
            )
            session.execute(stmt)
        session.commit()
