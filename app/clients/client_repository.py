from sqlalchemy import func, select

from app.database.database_session import SessionLocal
from app.database.models import Client, Project


def _find_by_name_ci(session, name):
    """Client dont le nom (trime) correspond, insensible a la casse/espaces.
    Sert a empecher les doublons type 'Loic Sallet' / ' loic sallet '."""
    key = name.strip().lower()
    return session.execute(
        select(Client).where(func.lower(func.trim(Client.name)) == key)
    ).scalar_one_or_none()


def _project_count(session, client_id):
    return session.execute(
        select(func.count(Project.id)).where(Project.client_id == client_id)
    ).scalar() or 0


def list_all():
    with SessionLocal() as session:
        counts = dict(
            session.execute(
                select(Project.client_id, func.count(Project.id))
                .where(Project.client_id.is_not(None))
                .group_by(Project.client_id)
            ).all()
        )
        clients = session.execute(
            select(Client).order_by(func.lower(Client.name))
        ).scalars().all()
        return [
            {"id": c.id, "name": c.name, "project_count": counts.get(c.id, 0)}
            for c in clients
        ]


def create(name):
    """Cree un client (nom trime). None si un client equivalent existe deja."""
    name = name.strip()
    with SessionLocal() as session:
        if _find_by_name_ci(session, name) is not None:
            return None
        client = Client(name=name)
        session.add(client)
        session.commit()
        session.refresh(client)
        return {"id": client.id, "name": client.name, "project_count": 0}


def rename(client_id, name):
    """'not_found' | 'duplicate' | {id, name}."""
    name = name.strip()
    with SessionLocal() as session:
        client = session.get(Client, client_id)
        if client is None:
            return "not_found"
        dup = _find_by_name_ci(session, name)
        if dup is not None and dup.id != client_id:
            return "duplicate"
        client.name = name
        session.commit()
        return {"id": client.id, "name": client.name}


def delete(client_id):
    """'not_found' | 'has_projects' | {name}. Refuse si le client a des projets."""
    with SessionLocal() as session:
        client = session.get(Client, client_id)
        if client is None:
            return "not_found"
        if _project_count(session, client_id) > 0:
            return "has_projects"
        name = client.name
        session.delete(client)
        session.commit()
        return {"name": name}