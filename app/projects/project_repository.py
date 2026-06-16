from datetime import datetime, timezone

from sqlalchemy import case, func, select

from app.common.enums import StateEnum
from app.database.database_session import SessionLocal
from app.database.models import Client, Employee, Project, Segment

_ACTIVE = StateEnum.ACTIVE.value


def _to_dict(p: Project):
    """Serialise un projet en parlant 'noms' (client, external_id) pour l'API."""
    return {
        "id": p.id,
        "client_id": p.client_id,
        "client": p.client.name if p.client else "",
        "video_name": p.video_name,
        "version": p.version,
        "estimated_duration_sec": p.estimated_duration_sec,
        "assigned_employee_id": p.employee.external_id if p.employee else None,
        "assigned_employee_name": p.employee.name if p.employee else None,
        "status": p.status,
        "completed_at": p.completed_at.isoformat() if p.completed_at else None,
        "completed_by": p.completed_by,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


def _get_or_create_client(session, name):
    name = (name or "").strip()
    client = session.execute(
        select(Client).where(Client.name == name)
    ).scalar_one_or_none()
    if client is None:
        client = Client(name=name)
        session.add(client)
        session.flush()
    return client.id


def _resolve_client(session, data):
    """Client du projet : `client_id` selectionne en priorite ; sinon get-or-create
    par nom (retro-compatibilite). None si rien -> contrainte NOT NULL en base."""
    cid = data.get("client_id")
    if cid:
        return cid
    name = (data.get("client") or "").strip()
    return _get_or_create_client(session, name) if name else None


def _resolve_employee(session, external_id):
    if not external_id:
        return None
    return session.execute(
        select(Employee.id).where(Employee.external_id == external_id)
    ).scalar_one_or_none()


def _spent_lookup(session):
    """Temps actif reellement travaille, par projet (project_id -> secondes)."""
    active = func.sum(
        case((Segment.state == _ACTIVE, Segment.duration_sec), else_=0)
    )
    rows = session.execute(
        select(Segment.project_id, active)
        .where(Segment.project_id.is_not(None))
        .group_by(Segment.project_id)
    ).all()
    return {r[0]: (r[1] or 0) for r in rows}


def list_all():
    with SessionLocal() as session:
        projects = session.execute(
            select(Project).order_by(Project.id.desc())
        ).scalars().all()
        spent = _spent_lookup(session)
        result = []
        for p in projects:
            d = _to_dict(p)
            d["spent_sec"] = spent.get(p.id, 0)
            result.append(d)
        return result


def list_for_employee(external_id):
    with SessionLocal() as session:
        emp_id = _resolve_employee(session, external_id)
        if emp_id is None:
            return []
        projects = session.execute(
            select(Project)
            .where(
                Project.assigned_employee_id == emp_id,
                Project.status != "termine",  # un projet termine sort de l'agent
            )
            .order_by(Project.id.desc())
        ).scalars().all()
        return [_to_dict(p) for p in projects]


def create(data):
    with SessionLocal() as session:
        project = Project(
            client_id=_resolve_client(session, data),
            video_name=data["video_name"].strip(),
            version=data["version"].strip(),
            estimated_duration_sec=data.get("estimated_duration_sec", 0),
            assigned_employee_id=_resolve_employee(
                session, data.get("assigned_employee_id")
            ),
        )
        session.add(project)
        session.commit()
        session.refresh(project)
        return _to_dict(project)


def update(project_id, data):
    with SessionLocal() as session:
        project = session.get(Project, project_id)
        if project is None:
            return None
        project.client_id = _resolve_client(session, data)
        project.video_name = data["video_name"].strip()
        project.version = data["version"].strip()
        project.estimated_duration_sec = data.get("estimated_duration_sec", 0)
        project.assigned_employee_id = _resolve_employee(
            session, data.get("assigned_employee_id")
        )
        session.commit()
        session.refresh(project)
        return _to_dict(project)


def get_dict(project_id):
    with SessionLocal() as session:
        project = session.get(Project, project_id)
        return _to_dict(project) if project else None


def delete(project_id):
    with SessionLocal() as session:
        project = session.get(Project, project_id)
        if project is None:
            return False
        session.delete(project)
        session.commit()
        return True


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def set_status(project_id, status, by=None):
    """Manager : passe le projet en 'termine' / 'en_cours'. None si introuvable."""
    with SessionLocal() as session:
        project = session.get(Project, project_id)
        if project is None:
            return None
        project.status = status
        if status == "termine":
            project.completed_at = _now()
            project.completed_by = by
        else:
            project.completed_at = None
            project.completed_by = None
        session.commit()
        session.refresh(project)
        return _to_dict(project)


def complete_for_employee(external_id, project_id):
    """Agent : un monteur marque SON projet termine. Renvoie 'forbidden' si le
    projet ne lui est pas assigne, 'not_found' si introuvable, sinon le projet."""
    with SessionLocal() as session:
        emp = session.execute(
            select(Employee).where(Employee.external_id == external_id)
        ).scalar_one_or_none()
        if emp is None:
            return "forbidden"
        project = session.get(Project, project_id)
        if project is None:
            return "not_found"
        if project.assigned_employee_id != emp.id:
            return "forbidden"
        project.status = "termine"
        project.completed_at = _now()
        project.completed_by = emp.name or external_id
        session.commit()
        session.refresh(project)
        return _to_dict(project)


def register_employee(external_id, name):
    """Get-or-create du monteur (registre) sans attendre d'activite : il devient
    visible et assignable des que le nom est configure dans l'agent."""
    if not external_id:
        return {"status": "ignored"}
    with SessionLocal() as session:
        emp = session.execute(
            select(Employee).where(Employee.external_id == external_id)
        ).scalar_one_or_none()
        if emp is None:
            emp = Employee(external_id=external_id, name=name or None)
            session.add(emp)
        elif name and emp.name != name:
            emp.name = name  # le nom courant fait foi
        session.commit()
    return {"status": "ok", "employee_id": external_id, "employee_name": name}


def list_employees():
    """Monteurs connus (registre employees), nom courant."""
    with SessionLocal() as session:
        rows = session.execute(
            select(Employee.external_id, Employee.name, Employee.role)
            .where(Employee.is_active.is_(True))
            .order_by(Employee.name)
        ).all()
    return [
        {
            "employee_id": r.external_id,
            "employee_name": r.name or r.external_id,
            "role": r.role,
        }
        for r in rows
    ]


def set_employee_role(external_id, role):
    """Definit le role metier d'un collaborateur. None/"" = efface."""
    with SessionLocal() as session:
        emp = session.execute(
            select(Employee).where(Employee.external_id == external_id)
        ).scalar_one_or_none()
        if emp is None:
            return None
        emp.role = role or None
        session.commit()
        return {
            "employee_id": emp.external_id,
            "employee_name": emp.name or emp.external_id,
            "role": emp.role,
        }
