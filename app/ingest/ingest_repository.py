from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.database.database import engine
from app.database.database_session import SessionLocal
from app.database.models import Segment


def _insert_stmt():
    """INSERT ... ON CONFLICT DO NOTHING selon le dialecte (ignore les doublons)."""
    return pg_insert if engine.dialect.name == "postgresql" else sqlite_insert


def insert_segments(events):
    """Insere une liste d'evenements (doublons ignores).

    Renvoie le nombre de lignes inserees. Une erreur de base remonte (pas de
    capture) pour que l'endpoint renvoie 500 et que l'agent reessaie -> pas de
    perte de donnees.
    """
    if not events:
        return 0

    now = datetime.now(timezone.utc).isoformat()
    rows = [
        {
            "employee_id": e.employee_id,
            "employee_name": e.employee_name,
            "client": e.client,
            "app": e.app,
            "window_title": e.window_title,
            "project": e.project,
            "version": e.version,
            "state": e.state,
            "start_ts": e.start_ts,
            "end_ts": e.end_ts,
            "duration_sec": e.duration_sec,
            "received_at": now,
        }
        for e in events
    ]

    stmt = _insert_stmt()(Segment).values(rows).on_conflict_do_nothing()
    with SessionLocal() as session:
        result = session.execute(stmt)
        session.commit()

    return result.rowcount if result.rowcount and result.rowcount > 0 else 0
