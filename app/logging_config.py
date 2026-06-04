import logging
import os
from logging.handlers import TimedRotatingFileHandler

from app.env.settings import BASE_DIR

LOG_PATH = os.path.join(BASE_DIR, "server.log")
LOGGER_NAME = "activity"

_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
_configured = False


def setup_logging():
    """Configure le logger applicatif : fichier rotatif quotidien (7 jours)
    + console. Idempotent (appelable plusieurs fois sans dupliquer les sorties).
    """
    global _configured
    logger = logging.getLogger(LOGGER_NAME)
    if _configured:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(_FORMAT)

    file_handler = TimedRotatingFileHandler(
        LOG_PATH, when="midnight", interval=1, backupCount=7, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.propagate = False  # evite la double sortie via le root logger

    _configured = True
    return logger


def get_logger():
    """Renvoie le logger applicatif (a utiliser partout dans le code)."""
    return logging.getLogger(LOGGER_NAME)
