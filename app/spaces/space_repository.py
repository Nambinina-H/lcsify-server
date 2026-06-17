from sqlalchemy import func, select
from sqlalchemy import update as sa_update

from app.database.database_session import SessionLocal
from app.database.models import Employee, Space


def _to_dict(s: Space, member_count: int):
    return {
        "id": s.id,
        "name": s.name,
        "color": s.color,
        "icon": s.icon,
        "member_count": member_count,
    }


def _member_count(session, space_id):
    return session.execute(
        select(func.count(Employee.id)).where(
            Employee.space_id == space_id, Employee.is_active.is_(True)
        )
    ).scalar_one()


def _assign_members(session, space_id, external_ids):
    """Affecte EXACTEMENT `external_ids` a l'espace (un collaborateur = un seul
    espace). Retire ceux qui n'y sont plus, ajoute/deplace les selectionnes."""
    # 1. Retire de cet espace les collaborateurs deselectionnes.
    session.execute(
        sa_update(Employee)
        .where(Employee.space_id == space_id)
        .values(space_id=None)
    )
    # 2. Affecte les selectionnes (ecrase leur espace precedent eventuel).
    if external_ids:
        session.execute(
            sa_update(Employee)
            .where(Employee.external_id.in_(external_ids))
            .values(space_id=space_id)
        )


def list_all():
    """Espaces tries par nom, avec le nombre de membres (collaborateurs actifs)."""
    with SessionLocal() as session:
        counts = dict(
            session.execute(
                select(Employee.space_id, func.count(Employee.id))
                .where(
                    Employee.space_id.is_not(None), Employee.is_active.is_(True)
                )
                .group_by(Employee.space_id)
            ).all()
        )
        spaces = session.execute(select(Space).order_by(Space.name)).scalars().all()
        return [_to_dict(s, counts.get(s.id, 0)) for s in spaces]


def create(data, member_ids):
    with SessionLocal() as session:
        s = Space(name=data["name"], color=data["color"], icon=data["icon"])
        session.add(s)
        session.flush()
        _assign_members(session, s.id, member_ids or [])
        count = _member_count(session, s.id)
        session.commit()
        return _to_dict(s, count)


def update(space_id, data, member_ids):
    with SessionLocal() as session:
        s = session.get(Space, space_id)
        if s is None:
            return None
        s.name = data["name"]
        s.color = data["color"]
        s.icon = data["icon"]
        _assign_members(session, space_id, member_ids or [])
        count = _member_count(session, space_id)
        session.commit()
        return _to_dict(s, count)


def delete(space_id):
    with SessionLocal() as session:
        s = session.get(Space, space_id)
        if s is None:
            return None
        name = s.name
        # Detache les membres explicitement (ne depend pas du ON DELETE SET NULL,
        # inactif sous SQLite sans PRAGMA) : le collaborateur reste, sans espace.
        session.execute(
            sa_update(Employee)
            .where(Employee.space_id == space_id)
            .values(space_id=None)
        )
        session.delete(s)
        session.commit()
        return {"id": space_id, "name": name}