from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.audit import audit_service
from app.leaves import leaves_service
from app.leaves.schemas import (
    LEAVE_STATUSES,
    LEAVE_TYPES,
    HrCollaborateurIn,
    HrLinkIn,
    LeaveIn,
    LeaveStatusIn,
)
from app.security.scopes import require_scope

router = APIRouter()

_manage = require_scope("leaves", "manage")


def _hr_label(hr: dict) -> str:
    nom = " ".join(filter(None, [hr.get("prenom"), hr.get("nom")]))
    return f"{nom} ({hr.get('matricule')})" if nom else (hr.get("matricule") or "")


# --- Registre RH (fiches de conges) ------------------------------------------


@router.get("/api/admin/hr-collaborateurs")
def list_hr(_=Depends(_manage)):
    """Registre RH : matricule, nom, solde courant (calcule), collaborateurs reliés."""
    return leaves_service.list_hr()


@router.post("/api/admin/hr-collaborateurs")
def create_hr(payload: HrCollaborateurIn, user=Depends(_manage)):
    created = leaves_service.create_hr(payload)
    audit_service.log_event(
        user, "hr.create", f"Fiche RH « {_hr_label(created)} » créée"
    )
    return created


@router.post("/api/admin/hr-collaborateurs/import")
async def import_hr(
    file: UploadFile = File(...),
    date_solde: str = Form(""),
    user=Depends(_manage),
):
    """Import du fichier RH (.xlsx / .csv). `date_solde` = date de reference des
    soldes (vide -> aujourd'hui). Upsert par matricule."""
    content = await file.read()
    ref = _parse_date(date_solde) or _local_today()
    result = leaves_service.import_roster(file.filename, content, ref)
    audit_service.log_event(
        user,
        "hr.import",
        f"Import RH : {result['created']} créé(s), {result['updated']} mis à jour",
        details=result,
    )
    return result


@router.put("/api/admin/hr-collaborateurs/{hr_id}")
def update_hr(hr_id: int, payload: HrCollaborateurIn, user=Depends(_manage)):
    updated = leaves_service.update_hr(hr_id, payload)
    if updated is None:
        raise HTTPException(status_code=404, detail="Fiche RH introuvable")
    audit_service.log_event(
        user, "hr.update", f"Fiche RH « {_hr_label(updated)} » modifiée"
    )
    return updated


@router.delete("/api/admin/hr-collaborateurs/{hr_id}")
def delete_hr(hr_id: int, user=Depends(_manage)):
    deleted = leaves_service.delete_hr(hr_id)
    if deleted is None:
        raise HTTPException(status_code=404, detail="Fiche RH introuvable")
    audit_service.log_event(
        user, "hr.delete", f"Fiche RH « {deleted['matricule']} » supprimée"
    )
    return {"status": "ok"}


# --- Conges ------------------------------------------------------------------


@router.get("/api/admin/leaves")
def list_leaves(hr_id: int | None = None, _=Depends(_manage)):
    return leaves_service.list_leaves(hr_id)


@router.post("/api/admin/leaves")
def create_leave(payload: LeaveIn, user=Depends(_manage)):
    _validate(payload)
    created = leaves_service.create_leave(payload, _user_name(user))
    if created is None:
        raise HTTPException(status_code=404, detail="Fiche RH introuvable")
    audit_service.log_event(
        user,
        "leave.create",
        _leave_line(_TYPE_LABELS.get(created["type"], created["type"]), created),
    )
    return created


@router.put("/api/admin/leaves/{leave_id}")
def update_leave(leave_id: int, payload: LeaveIn, user=Depends(_manage)):
    _validate(payload)
    updated = leaves_service.update_leave(leave_id, payload)
    if updated is None:
        raise HTTPException(status_code=404, detail="Congé ou fiche RH introuvable")
    audit_service.log_event(
        user, "leave.update", _leave_line("Congé modifié", updated)
    )
    return updated


@router.patch("/api/admin/leaves/{leave_id}/status")
def set_leave_status(leave_id: int, payload: LeaveStatusIn, user=Depends(_manage)):
    """Valide / refuse / remet en attente un congé (depuis le tableau)."""
    if payload.statut not in LEAVE_STATUSES:
        raise HTTPException(status_code=422, detail="Statut invalide")
    updated = leaves_service.set_leave_status(
        leave_id, payload.statut, _user_name(user)
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Congé introuvable")
    audit_service.log_event(
        user,
        "leave.status",
        _leave_line(
            f"Congé {_STATUT_LABELS.get(payload.statut, payload.statut)}",
            updated,
            with_days=False,
        ),
    )
    return updated


@router.delete("/api/admin/leaves/{leave_id}")
def delete_leave(leave_id: int, user=Depends(_manage)):
    deleted = leaves_service.delete_leave(leave_id)
    if deleted is None:
        raise HTTPException(status_code=404, detail="Congé introuvable")
    audit_service.log_event(
        user, "leave.delete", _leave_line("Congé supprimé", deleted, with_days=False)
    )
    return {"status": "ok"}


# --- Lien collaborateur (agent) <-> fiche RH ---------------------------------


@router.patch("/api/admin/employees/{employee_id}/hr-link")
def link_employee(employee_id: str, payload: HrLinkIn, user=Depends(_manage)):
    """Rattache un collaborateur (agent) a une fiche RH (ou le detache)."""
    result = leaves_service.set_employee_hr(employee_id, payload.hr_collaborateur_id)
    if result == "emp_not_found":
        raise HTTPException(status_code=404, detail="Collaborateur introuvable")
    if result == "hr_not_found":
        raise HTTPException(status_code=404, detail="Fiche RH introuvable")
    audit_service.log_event(
        user,
        "hr.link",
        f"{result['employee_name']} relié à "
        + (result["hr_matricule"] or "(aucune fiche)"),
    )
    return result


# --- Helpers -----------------------------------------------------------------


_TYPE_LABELS = {
    "permission": "Permission exceptionnelle",
    "conge_paye": "Congé payé",
    "sans_solde": "Congé sans solde",
    "autre": "Autre",
}
_STATUT_LABELS = {
    "approuve": "approuvé",
    "refuse": "refusé",
    "en_attente": "remis en attente",
}


def _ddmm(iso: str) -> str:
    """« 2026-06-10 » -> « 10/06 »."""
    parts = (iso or "").split("-")
    return f"{parts[2]}/{parts[1]}" if len(parts) == 3 else (iso or "")


def _person(lv: dict) -> str:
    name = " ".join(filter(None, [lv.get("prenom"), lv.get("nom")])) or lv.get(
        "matricule"
    )
    return f"{name} ({lv.get('matricule')})"


def _days(lv: dict) -> str:
    n = lv.get("nb_jours") or 0
    return (f"{int(n)}" if float(n).is_integer() else f"{n}") + " j"


def _leave_line(prefix: str, lv: dict, with_days: bool = True) -> str:
    """« <prefix> : Prénom Nom (Matricule), 10/06→12/06 [, 5 j] »."""
    base = (
        f"{prefix} : {_person(lv)}, "
        f"{_ddmm(lv['date_debut'])}→{_ddmm(lv['date_fin'])}"
    )
    return f"{base}, {_days(lv)}" if with_days else base


def _validate(payload: LeaveIn):
    if payload.type not in LEAVE_TYPES:
        raise HTTPException(status_code=422, detail="Type de congé invalide")
    if payload.date_fin < payload.date_debut:
        raise HTTPException(
            status_code=422, detail="La date de fin précède la date de début"
        )


def _user_name(user) -> str | None:
    from app.auth import auth_repository

    db_user = auth_repository.get_by_id(user["id"]) if user.get("id") else None
    return db_user.name if db_user else None


def _parse_date(value: str):
    value = (value or "").strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _local_today() -> date:
    return (datetime.now(timezone.utc) + timedelta(hours=3)).date()
