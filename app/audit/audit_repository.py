from datetime import datetime

from sqlalchemy import func, select

from app.database.database_session import SessionLocal
from app.database.models import AuditLog


def _parse_day(value: str, end: bool):
    """'YYYY-MM-DD' -> datetime borne (00:00:00 ou 23:59:59). None si invalide."""
    try:
        d = datetime.fromisoformat(value)
    except ValueError:
        return None
    return d.replace(hour=23, minute=59, second=59) if end else d


def record(user_id, user_label, action, summary, details=None):
    with SessionLocal() as session:
        session.add(
            AuditLog(
                user_id=user_id,
                user_label=user_label,
                action=action,
                summary=summary,
                details=details,
            )
        )
        session.commit()


def list_page(
    page: int,
    page_size: int,
    q: str = "",
    action: str = "",
    date_from: str = "",
    date_to: str = "",
):
    """Evenements du plus recent au plus ancien, pagines.
    q : recherche texte ; action : filtre exact ; date_from/date_to : plage."""
    filters = []
    if q:
        like = f"%{q}%"
        filters.append(
            AuditLog.summary.ilike(like) | AuditLog.user_label.ilike(like)
        )
    if action:
        filters.append(AuditLog.action == action)
    lo = _parse_day(date_from, end=False) if date_from else None
    hi = _parse_day(date_to, end=True) if date_to else None
    if lo:
        filters.append(AuditLog.created_at >= lo)
    if hi:
        filters.append(AuditLog.created_at <= hi)
    with SessionLocal() as session:
        total = session.execute(
            select(func.count(AuditLog.id)).where(*filters)
        ).scalar() or 0
        rows = session.execute(
            select(AuditLog)
            .where(*filters)
            .order_by(AuditLog.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).scalars().all()
        events = [
            {
                "id": r.id,
                "user": r.user_label or "(systeme)",
                "action": r.action,
                "summary": r.summary,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    return {"events": events, "total": total}
