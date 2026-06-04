from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base

from app.env.settings import DATABASE_URL, SQLITE_URL
from app.logging_config import get_logger

logger = get_logger()


def _build_engine():
    """Cree l'engine SQLAlchemy.

    Si une URL PostgreSQL est configuree, on tente de s'y connecter ; si Postgres
    n'est pas disponible, on **se replie sur SQLite** (le serveur reste utilisable).
    """
    url = DATABASE_URL
    if url.startswith("postgresql"):
        try:
            eng = create_engine(url, pool_pre_ping=True)
            with eng.connect() as conn:
                conn.execute(text("SELECT 1"))
            return eng, "PostgreSQL"
        except Exception as exc:
            logger.warning("PostgreSQL indisponible (%s). Repli sur SQLite.", exc)
            url = SQLITE_URL

    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args), "SQLite"


engine, DB_KIND = _build_engine()
Base = declarative_base()
