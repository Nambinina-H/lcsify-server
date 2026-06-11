import json

from app.audit import audit_repository
from app.auth import auth_repository
from app.logging_config import get_logger

logger = get_logger()


def log_event(user, action: str, summary: str, details: dict | None = None):
    """Enregistre un evenement d'audit. Ne doit JAMAIS faire echouer l'action
    metier : toute erreur est avalee (loggee seulement).

    user : dict {id, role} (get_current_user) ou objet User (login).
    """
    try:
        if isinstance(user, dict):
            user_id = user.get("id")
            db_user = auth_repository.get_by_id(user_id) if user_id else None
            label = db_user.name if db_user else None
        else:  # objet User (ex. login)
            user_id = user.id
            label = user.name
        audit_repository.record(
            user_id=user_id,
            user_label=label,
            action=action,
            summary=summary,
            details=json.dumps(details, ensure_ascii=False) if details else None,
        )
    except Exception:
        logger.exception("Audit impossible pour l'action %s", action)


def list_events(
    page: int,
    page_size: int,
    q: str = "",
    action: str = "",
    date_from: str = "",
    date_to: str = "",
):
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    return audit_repository.list_page(
        page, page_size, q.strip(), action.strip(), date_from.strip(), date_to.strip()
    )
