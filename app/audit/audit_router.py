from fastapi import APIRouter, Depends

from app.audit import audit_service
from app.security.scopes import require_scope

router = APIRouter()


@router.get("/api/admin/audit")
def list_audit(
    page: int = 1,
    page_size: int = 15,
    q: str = "",
    action: str = "",
    date_from: str = "",
    date_to: str = "",
    _=Depends(require_scope("history", "view")),
):
    """Journal d'audit (admin) : du plus recent au plus ancien, pagine.
    q : recherche ; action : type ; date_from/date_to : plage (YYYY-MM-DD)."""
    return audit_service.list_events(page, page_size, q, action, date_from, date_to)
