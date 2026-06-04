from sqlalchemy import and_, case, func, select

from app.common.enums import StateEnum
from app.database.database_session import SessionLocal
from app.database.models import Segment

_ACTIVE = StateEnum.ACTIVE.value
_IDLE = StateEnum.IDLE.value
_PAUSED = StateEnum.PAUSED.value


def _sum_state(state):
    return func.sum(
        case((Segment.state == state, Segment.duration_sec), else_=0)
    )


def _rows(stmt):
    with SessionLocal() as session:
        return session.execute(stmt).mappings().all()


def fetch_summary_totals(lo, hi):
    active = _sum_state(_ACTIVE).label("active_sec")
    stmt = (
        select(
            Segment.employee_id,
            func.max(Segment.employee_name).label("employee_name"),
            active,
            _sum_state(_IDLE).label("idle_sec"),
            _sum_state(_PAUSED).label("paused_sec"),
            func.max(Segment.end_ts).label("last_seen"),
        )
        .where(Segment.start_ts >= lo, Segment.start_ts <= hi)
        .group_by(Segment.employee_id)
        .order_by(active.desc())
    )
    return _rows(stmt)


def fetch_current_activity():
    """Derniere mesure connue de chaque monteur (app + titre en cours)."""
    sub = (
        select(
            Segment.employee_id,
            func.max(Segment.end_ts).label("m"),
        )
        .group_by(Segment.employee_id)
        .subquery()
    )
    stmt = select(
        Segment.employee_id,
        Segment.app,
        Segment.window_title,
        Segment.project,
        Segment.state,
        Segment.end_ts,
    ).join(
        sub,
        and_(Segment.employee_id == sub.c.employee_id, Segment.end_ts == sub.c.m),
    )
    return _rows(stmt)


def fetch_projects(lo, hi, employee_id):
    project = func.coalesce(Segment.project, "(non identifie)")
    total = func.sum(Segment.duration_sec).label("active_sec")
    stmt = select(
        project.label("project"), Segment.employee_id, total
    ).where(Segment.state == _ACTIVE, Segment.start_ts >= lo, Segment.start_ts <= hi)
    if employee_id:
        stmt = stmt.where(Segment.employee_id == employee_id)
    stmt = stmt.group_by(project, Segment.employee_id).order_by(total.desc())
    return _rows(stmt)


def fetch_apps(lo, hi, employee_id):
    total = func.sum(Segment.duration_sec).label("active_sec")
    stmt = select(Segment.app, total).where(
        Segment.state == _ACTIVE, Segment.start_ts >= lo, Segment.start_ts <= hi
    )
    if employee_id:
        stmt = stmt.where(Segment.employee_id == employee_id)
    stmt = stmt.group_by(Segment.app).order_by(total.desc()).limit(20)
    return _rows(stmt)


def fetch_details(lo, hi, employee_id):
    title = func.coalesce(func.nullif(Segment.window_title, ""), "(sans titre)")
    total = func.sum(Segment.duration_sec).label("active_sec")
    stmt = select(
        Segment.app, title.label("window_title"), Segment.project, total
    ).where(Segment.state == _ACTIVE, Segment.start_ts >= lo, Segment.start_ts <= hi)
    if employee_id:
        stmt = stmt.where(Segment.employee_id == employee_id)
    stmt = stmt.group_by(Segment.app, title).order_by(total.desc()).limit(40)
    return _rows(stmt)


def fetch_timeline(employee_id, lo, hi):
    stmt = (
        select(
            Segment.app,
            Segment.window_title,
            Segment.project,
            Segment.state,
            Segment.start_ts,
            Segment.end_ts,
            Segment.duration_sec,
        )
        .where(
            Segment.employee_id == employee_id,
            Segment.start_ts >= lo,
            Segment.start_ts <= hi,
        )
        .order_by(Segment.start_ts)
    )
    return _rows(stmt)
