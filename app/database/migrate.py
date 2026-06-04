import os

from alembic import command
from alembic.config import Config

from app.database.database import DB_KIND
from app.env.settings import BASE_DIR
from app.logging_config import get_logger

logger = get_logger()


def run_migrations():
    """Applique les migrations Alembic jusqu'a la derniere (cree/maj le schema).

    Sur une base vierge (ex. Postgres Railway) : cree toutes les tables.
    Sur une base deja a jour : ne fait rien.
    """
    cfg = Config(os.path.join(BASE_DIR, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(BASE_DIR, "alembic"))
    command.upgrade(cfg, "head")
    logger.info("Base de donnees : %s (migrations a jour)", DB_KIND)
