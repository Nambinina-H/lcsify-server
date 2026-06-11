from sqlalchemy import and_, case, func, select

from app.common.enums import StateEnum
from app.database.database_session import SessionLocal
from app.database.models import Client, Employee, Project, Segment

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
            Employee.external_id.label("employee_id"),
            func.max(Employee.name).label("employee_name"),
            active,
            _sum_state(_IDLE).label("idle_sec"),
            _sum_state(_PAUSED).label("paused_sec"),
            func.max(Segment.ended_at).label("last_seen"),
        )
        .join(Employee, Segment.employee_id == Employee.id)
        .where(Segment.started_at >= lo, Segment.started_at <= hi)
        .group_by(Employee.external_id)
        .order_by(active.desc())
    )
    return _rows(stmt)


def fetch_current_activity():
    """Derniere mesure connue de chaque monteur (app + titre + projet en cours)."""
    sub = (
        select(
            Segment.employee_id,
            func.max(Segment.ended_at).label("m"),
        )
        .group_by(Segment.employee_id)
        .subquery()
    )
    stmt = (
        select(
            Employee.external_id.label("employee_id"),
            Segment.app,
            Segment.window_title,
            Project.video_name.label("project"),
            Segment.state,
            Segment.ended_at,
        )
        .join(
            sub,
            and_(
                Segment.employee_id == sub.c.employee_id,
                Segment.ended_at == sub.c.m,
            ),
        )
        .join(Employee, Segment.employee_id == Employee.id)
        .outerjoin(Project, Segment.project_id == Project.id)
    )
    return _rows(stmt)


def fetch_projects(lo, hi, employee_id):
    project = func.coalesce(Project.video_name, "(non identifie)")
    total = func.sum(Segment.duration_sec).label("active_sec")
    stmt = (
        select(
            project.label("project"),
            Employee.external_id.label("employee_id"),
            total,
        )
        .join(Employee, Segment.employee_id == Employee.id)
        .outerjoin(Project, Segment.project_id == Project.id)
        .where(
            Segment.state == _ACTIVE,
            Segment.started_at >= lo,
            Segment.started_at <= hi,
        )
    )
    if employee_id:
        stmt = stmt.where(Employee.external_id == employee_id)
    stmt = stmt.group_by(project, Employee.external_id).order_by(total.desc())
    return _rows(stmt)


def fetch_apps(lo, hi, employee_id):
    total = func.sum(Segment.duration_sec).label("active_sec")
    stmt = (
        select(Segment.app, total)
        .join(Employee, Segment.employee_id == Employee.id)
        .where(
            Segment.state == _ACTIVE,
            Segment.started_at >= lo,
            Segment.started_at <= hi,
        )
    )
    if employee_id:
        stmt = stmt.where(Employee.external_id == employee_id)
    stmt = stmt.group_by(Segment.app).order_by(total.desc()).limit(20)
    return _rows(stmt)


def fetch_details(lo, hi, employee_id):
    title = func.coalesce(func.nullif(Segment.window_title, ""), "(sans titre)")
    project = func.coalesce(Project.video_name, "(non identifie)")
    total = func.sum(Segment.duration_sec).label("active_sec")
    stmt = (
        select(
            Segment.app,
            title.label("window_title"),
            project.label("project"),
            total,
        )
        .join(Employee, Segment.employee_id == Employee.id)
        .outerjoin(Project, Segment.project_id == Project.id)
        .where(
            Segment.state == _ACTIVE,
            Segment.started_at >= lo,
            Segment.started_at <= hi,
        )
    )
    if employee_id:
        stmt = stmt.where(Employee.external_id == employee_id)
    stmt = (
        stmt.group_by(Segment.app, title, project)
        .order_by(total.desc())
        .limit(40)
    )
    return _rows(stmt)


def fetch_calendar(lo, hi, employee_id):
    """Activite reelle agregee par jour / monteur / livrable."""
    day = func.date(Segment.started_at).label("day")
    client = func.coalesce(Client.name, "").label("client")
    project = func.coalesce(Project.video_name, "(non identifie)").label("project")
    version = func.coalesce(Project.version, "").label("version")
    stmt = (
        select(
            day,
            Employee.external_id.label("employee_id"),
            func.max(Employee.name).label("employee_name"),
            client,
            project,
            version,
            _sum_state(_ACTIVE).label("active_sec"),
            _sum_state(_IDLE).label("idle_sec"),
        )
        .join(Employee, Segment.employee_id == Employee.id)
        .outerjoin(Project, Segment.project_id == Project.id)
        .outerjoin(Client, Project.client_id == Client.id)
        .where(Segment.started_at >= lo, Segment.started_at <= hi)
    )
    if employee_id:
        stmt = stmt.where(Employee.external_id == employee_id)
    stmt = stmt.group_by(
        day, Employee.external_id, client, project, version
    ).order_by(day)
    return _rows(stmt)


def fetch_project_meta(project_id):
    stmt = (
        select(
            Project.id,
            Project.video_name,
            Project.version,
            Project.estimated_duration_sec,
            Client.name.label("client"),
            Employee.name.label("employee_name"),
        )
        .outerjoin(Client, Project.client_id == Client.id)
        .outerjoin(Employee, Project.assigned_employee_id == Employee.id)
        .where(Project.id == project_id)
    )
    with SessionLocal() as session:
        return session.execute(stmt).mappings().first()


def fetch_project_daily(project_id):
    """Temps actif par jour pour un projet (pour le cumul dans le temps)."""
    day = func.date(Segment.started_at).label("day")
    active = _sum_state(_ACTIVE).label("active_sec")
    stmt = (
        select(day, active)
        .where(Segment.project_id == project_id)
        .group_by(day)
        .order_by(day)
    )
    return _rows(stmt)


def fetch_project_by_employee(project_id):
    active = func.sum(Segment.duration_sec).label("active_sec")
    stmt = (
        select(Employee.name.label("employee_name"), active)
        .join(Employee, Segment.employee_id == Employee.id)
        .where(Segment.project_id == project_id, Segment.state == _ACTIVE)
        .group_by(Employee.name)
        .order_by(active.desc())
    )
    return _rows(stmt)


def fetch_project_by_app(project_id):
    active = func.sum(Segment.duration_sec).label("active_sec")
    stmt = (
        select(Segment.app, active)
        .where(Segment.project_id == project_id, Segment.state == _ACTIVE)
        .group_by(Segment.app)
        .order_by(active.desc())
        .limit(15)
    )
    return _rows(stmt)


def fetch_day_segments(lo, hi, employee_id):
    """Tous les segments d'une journee, par monteur (pour la frise du jour)."""
    project = func.coalesce(Project.video_name, "(non identifie)")
    client = func.coalesce(Client.name, "").label("client")
    version = func.coalesce(Project.version, "").label("version")
    stmt = (
        select(
            Employee.external_id.label("employee_id"),
            Employee.name.label("employee_name"),
            project.label("project"),
            client,
            version,
            Segment.state,
            Segment.started_at.label("start_ts"),
            Segment.ended_at.label("end_ts"),
            Segment.duration_sec,
        )
        .join(Employee, Segment.employee_id == Employee.id)
        .outerjoin(Project, Segment.project_id == Project.id)
        .outerjoin(Client, Project.client_id == Client.id)
        .where(Segment.started_at >= lo, Segment.started_at <= hi)
    )
    if employee_id:
        stmt = stmt.where(Employee.external_id == employee_id)
    stmt = stmt.order_by(Employee.name, Segment.started_at)
    return _rows(stmt)


def fetch_timeline(employee_id, lo, hi):
    project = func.coalesce(Project.video_name, "(non identifie)")
    stmt = (
        select(
            Segment.app,
            Segment.window_title,
            project.label("project"),
            Segment.state,
            Segment.started_at.label("start_ts"),
            Segment.ended_at.label("end_ts"),
            Segment.duration_sec,
        )
        .join(Employee, Segment.employee_id == Employee.id)
        .outerjoin(Project, Segment.project_id == Project.id)
        .where(
            Employee.external_id == employee_id,
            Segment.started_at >= lo,
            Segment.started_at <= hi,
        )
        .order_by(Segment.started_at)
    )
    return _rows(stmt)
