from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy import update as sa_update

from app.database.database_session import SessionLocal
from app.database.models import Employee, HrCollaborateur, Leave
from app.leaves.schemas import PAID_TYPE

_ACCRUAL_PER_MONTH = 2.5  # +2,5 j a chaque fin de mois (demande du RH)
_LOCAL_OFFSET = timedelta(hours=3)  # Madagascar UTC+3


def _local_today() -> date:
    return (datetime.now(timezone.utc) + _LOCAL_OFFSET).date()


def _accrued_months(date_solde: date | None, today: date) -> int:
    """Nombre de fins de mois ecoulees depuis la date de reference (>= 0).

    Chaque passage a un nouveau mois = le mois precedent s'est termine -> +2,5 j.
    """
    if date_solde is None:
        return 0
    months = (today.year - date_solde.year) * 12 + (today.month - date_solde.month)
    return max(0, months)


def _solde(hr: HrCollaborateur, taken: float, today: date) -> float:
    accrued = _ACCRUAL_PER_MONTH * _accrued_months(hr.date_solde, today)
    return round((hr.solde_initial or 0.0) + accrued - (taken or 0.0), 2)


# --- Registre RH -------------------------------------------------------------


def _taken_by_hr(session) -> dict:
    """{hr_id: total jours de conges payes approuves}."""
    rows = session.execute(
        select(Leave.hr_id, func.sum(Leave.nb_jours))
        .where(Leave.type == PAID_TYPE, Leave.statut == "approuve")
        .group_by(Leave.hr_id)
    ).all()
    return {hr_id: (total or 0.0) for hr_id, total in rows}


def _linked_by_hr(session) -> dict:
    """{hr_id: [noms des collaborateurs (agent) relies]}."""
    rows = session.execute(
        select(Employee.hr_collaborateur_id, Employee.name, Employee.external_id)
        .where(Employee.hr_collaborateur_id.is_not(None),
               Employee.is_active.is_(True))
    ).all()
    out = {}
    for hr_id, name, ext in rows:
        out.setdefault(hr_id, []).append(name or ext)
    return out


def _hr_dict(hr: HrCollaborateur, taken: float, today: date, linked: list):
    return {
        "id": hr.id,
        "matricule": hr.matricule,
        "nom": hr.nom,
        "prenom": hr.prenom,
        "solde_initial": round(hr.solde_initial or 0.0, 2),
        "date_solde": hr.date_solde.isoformat() if hr.date_solde else None,
        "poste": hr.poste,
        "service": hr.service,
        "taken": round(taken or 0.0, 2),
        "solde": _solde(hr, taken, today),
        "linked_names": linked,
    }


def list_hr():
    with SessionLocal() as session:
        taken = _taken_by_hr(session)
        linked = _linked_by_hr(session)
        today = _local_today()
        rows = session.execute(
            select(HrCollaborateur).order_by(HrCollaborateur.matricule)
        ).scalars().all()
        return [
            _hr_dict(hr, taken.get(hr.id, 0.0), today, linked.get(hr.id, []))
            for hr in rows
        ]


def get_hr(hr_id):
    with SessionLocal() as session:
        hr = session.get(HrCollaborateur, hr_id)
        if hr is None:
            return None
        taken = _taken_by_hr(session).get(hr_id, 0.0)
        linked = _linked_by_hr(session).get(hr_id, [])
        return _hr_dict(hr, taken, _local_today(), linked)


def create_hr(data):
    with SessionLocal() as session:
        hr = HrCollaborateur(
            matricule=data["matricule"].strip(),
            nom=data.get("nom"),
            prenom=data.get("prenom"),
            solde_initial=data.get("solde_initial") or 0.0,
            date_solde=data.get("date_solde"),
            poste=data.get("poste"),
            service=data.get("service"),
        )
        session.add(hr)
        session.commit()
        session.refresh(hr)
        return _hr_dict(hr, 0.0, _local_today(), [])


def update_hr(hr_id, data):
    with SessionLocal() as session:
        hr = session.get(HrCollaborateur, hr_id)
        if hr is None:
            return None
        hr.matricule = data["matricule"].strip()
        hr.nom = data.get("nom")
        hr.prenom = data.get("prenom")
        hr.solde_initial = data.get("solde_initial") or 0.0
        hr.date_solde = data.get("date_solde")
        hr.poste = data.get("poste")
        hr.service = data.get("service")
        session.commit()
        session.refresh(hr)
        taken = _taken_by_hr(session).get(hr_id, 0.0)
        linked = _linked_by_hr(session).get(hr_id, [])
        return _hr_dict(hr, taken, _local_today(), linked)


def delete_hr(hr_id):
    """Supprime une fiche RH. Detache les collaborateurs relies et supprime ses
    conges explicitement (ON DELETE inactif sous SQLite)."""
    with SessionLocal() as session:
        hr = session.get(HrCollaborateur, hr_id)
        if hr is None:
            return None
        label = hr.matricule
        session.execute(
            sa_update(Employee)
            .where(Employee.hr_collaborateur_id == hr_id)
            .values(hr_collaborateur_id=None)
        )
        session.query(Leave).filter(Leave.hr_id == hr_id).delete(
            synchronize_session=False
        )
        session.delete(hr)
        session.commit()
        return {"id": hr_id, "matricule": label}


def import_roster(rows: list[dict], date_solde):
    """Upsert par matricule (le fichier RH fait foi). Met a jour solde + date de
    reference. Renvoie {created, updated, total}."""
    created = updated = 0
    with SessionLocal() as session:
        for r in rows:
            matricule = (r.get("matricule") or "").strip()
            if not matricule:
                continue
            hr = session.execute(
                select(HrCollaborateur).where(HrCollaborateur.matricule == matricule)
            ).scalar_one_or_none()
            if hr is None:
                hr = HrCollaborateur(matricule=matricule)
                session.add(hr)
                created += 1
            else:
                updated += 1
            if r.get("nom"):
                hr.nom = r["nom"]
            if r.get("prenom"):
                hr.prenom = r["prenom"]
            hr.solde_initial = r.get("solde_initial") or 0.0
            hr.date_solde = date_solde
            if r.get("poste"):
                hr.poste = r["poste"]
            if r.get("service"):
                hr.service = r["service"]
        session.commit()
    return {"created": created, "updated": updated, "total": created + updated}


# --- Conges ------------------------------------------------------------------


def _leave_dict(lv: Leave, hr: HrCollaborateur | None):
    return {
        "id": lv.id,
        "hr_id": lv.hr_id,
        "matricule": hr.matricule if hr else None,
        "nom": hr.nom if hr else None,
        "prenom": hr.prenom if hr else None,
        "type": lv.type,
        "date_debut": lv.date_debut.isoformat(),
        "date_fin": lv.date_fin.isoformat(),
        "nb_jours": round(lv.nb_jours or 0.0, 2),
        "motif": lv.motif,
        "statut": lv.statut,
        "validateur": lv.validateur,
        "created_by": lv.created_by,
        "created_at": lv.created_at.isoformat() if lv.created_at else None,
        "decided_by": lv.decided_by,
        "decided_at": lv.decided_at.isoformat() if lv.decided_at else None,
    }


def list_leaves(hr_id=None):
    with SessionLocal() as session:
        q = (
            select(Leave, HrCollaborateur)
            .join(HrCollaborateur, Leave.hr_id == HrCollaborateur.id)
            .order_by(Leave.date_debut.desc(), Leave.id.desc())
        )
        if hr_id is not None:
            q = q.where(Leave.hr_id == hr_id)
        return [_leave_dict(lv, hr) for lv, hr in session.execute(q).all()]


def create_leave(data, created_by=None):
    """Renvoie le conge cree, ou None si la fiche RH (hr_id) n'existe pas."""
    with SessionLocal() as session:
        hr = session.get(HrCollaborateur, data["hr_id"])
        if hr is None:
            return None
        lv = Leave(
            hr_id=data["hr_id"],
            type=data["type"],
            date_debut=data["date_debut"],
            date_fin=data["date_fin"],
            nb_jours=data.get("nb_jours") or 0.0,
            motif=data.get("motif"),
            validateur=data.get("validateur"),
            statut="en_attente",  # validation faite ensuite depuis le tableau
            created_by=created_by,
        )
        session.add(lv)
        session.commit()
        session.refresh(lv)
        return _leave_dict(lv, hr)


def update_leave(leave_id, data):
    with SessionLocal() as session:
        lv = session.get(Leave, leave_id)
        if lv is None:
            return None
        hr = session.get(HrCollaborateur, data["hr_id"])
        if hr is None:
            return None
        lv.hr_id = data["hr_id"]
        lv.type = data["type"]
        lv.date_debut = data["date_debut"]
        lv.date_fin = data["date_fin"]
        lv.nb_jours = data.get("nb_jours") or 0.0
        lv.motif = data.get("motif")
        lv.validateur = data.get("validateur")
        # Le statut n'est pas modifie ici : il se gere via set_leave_status.
        session.commit()
        session.refresh(lv)
        return _leave_dict(lv, hr)


def set_leave_status(leave_id, statut, decided_by=None):
    """Valide / refuse / remet en attente un conge, en tracant qui et quand.
    None si introuvable."""
    with SessionLocal() as session:
        lv = session.get(Leave, leave_id)
        if lv is None:
            return None
        lv.statut = statut
        lv.decided_by = decided_by
        lv.decided_at = datetime.now(timezone.utc).replace(tzinfo=None)
        session.commit()
        session.refresh(lv)
        hr = session.get(HrCollaborateur, lv.hr_id)
        return _leave_dict(lv, hr)


def delete_leave(leave_id):
    with SessionLocal() as session:
        lv = session.get(Leave, leave_id)
        if lv is None:
            return None
        hr = session.get(HrCollaborateur, lv.hr_id)
        info = _leave_dict(lv, hr)  # snapshot avant suppression (pour l'audit)
        session.delete(lv)
        session.commit()
        return info


# --- Lien collaborateur (agent) <-> fiche RH ---------------------------------


def set_employee_hr(external_id, hr_id):
    """Rattache/detache un collaborateur (agent) a une fiche RH.

    Renvoie 'emp_not_found' / 'hr_not_found' / dict du collaborateur.
    """
    with SessionLocal() as session:
        emp = session.execute(
            select(Employee).where(Employee.external_id == external_id)
        ).scalar_one_or_none()
        if emp is None:
            return "emp_not_found"
        matricule = None
        if hr_id is not None:
            hr = session.get(HrCollaborateur, hr_id)
            if hr is None:
                return "hr_not_found"
            matricule = hr.matricule
        emp.hr_collaborateur_id = hr_id
        session.commit()
        return {
            "employee_id": emp.external_id,
            "employee_name": emp.name or emp.external_id,
            "hr_collaborateur_id": hr_id,
            "hr_matricule": matricule,
        }
