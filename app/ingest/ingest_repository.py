from datetime import datetime, timezone

from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.database.database import engine
from app.database.database_session import SessionLocal
from app.database.models import Segment


def _insert_stmt():
    """INSERT ... ON CONFLICT DO NOTHING selon le dialecte (ignore les doublons)."""
    return pg_insert if engine.dialect.name == "postgresql" else sqlite_insert


def insert_segments(events):
    """Insère une liste d'événements (doublons ignorés).

    Propage aussi le **nom courant** de chaque monteur sur TOUT son historique :
    changer son nom dans l'agent met à jour toutes ses lignes (même `employee_id`).

    Une erreur de base remonte (pas de capture) pour que l'endpoint renvoie 500
    et que l'agent réessaie -> pas de perte de données.
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

    # Nom le plus récent par monteur (l'événement avec le end_ts le plus grand).
    latest_name = {}
    for e in events:
        ts = e.end_ts or ""
        current = latest_name.get(e.employee_id)
        if current is None or ts >= current[0]:
            latest_name[e.employee_id] = (ts, e.employee_name)

    stmt = _insert_stmt()(Segment).values(rows).on_conflict_do_nothing()
    with SessionLocal() as session:
        result = session.execute(stmt)
        # Aligne tout l'historique du monteur sur son nom courant (no-op si inchangé).
        for emp_id, (_, name) in latest_name.items():
            if name:
                session.execute(
                    update(Segment)
                    .where(
                        Segment.employee_id == emp_id,
                        Segment.employee_name.is_distinct_from(name),
                    )
                    .values(employee_name=name)
                )
        session.commit()

    return result.rowcount if result.rowcount and result.rowcount > 0 else 0
