from app.leaves import import_parser, leaves_repository
from app.leaves.schemas import HrCollaborateurIn, LeaveIn


# --- Registre RH -------------------------------------------------------------


def list_hr():
    return leaves_repository.list_hr()


def get_hr(hr_id):
    return leaves_repository.get_hr(hr_id)


def create_hr(payload: HrCollaborateurIn):
    return leaves_repository.create_hr(payload.model_dump())


def update_hr(hr_id, payload: HrCollaborateurIn):
    return leaves_repository.update_hr(hr_id, payload.model_dump())


def delete_hr(hr_id):
    return leaves_repository.delete_hr(hr_id)


def import_roster(filename, content, date_solde):
    rows = import_parser.parse(filename, content)
    result = leaves_repository.import_roster(rows, date_solde)
    return result


# --- Conges ------------------------------------------------------------------


def _calendar_days(date_debut, date_fin) -> int:
    """Jours calendaires inclus (week-ends compris) entre deux dates."""
    return (date_fin - date_debut).days + 1


def list_leaves(hr_id=None):
    return leaves_repository.list_leaves(hr_id)


def _normalize_leave(payload: LeaveIn) -> dict:
    data = payload.model_dump()
    # nb_jours non fourni (ou <= 0) -> calcul automatique en jours calendaires.
    if data.get("nb_jours") is None:
        data["nb_jours"] = float(_calendar_days(data["date_debut"], data["date_fin"]))
    return data


def create_leave(payload: LeaveIn, created_by=None):
    return leaves_repository.create_leave(_normalize_leave(payload), created_by)


def update_leave(leave_id, payload: LeaveIn):
    return leaves_repository.update_leave(leave_id, _normalize_leave(payload))


def set_leave_status(leave_id, statut, decided_by=None):
    return leaves_repository.set_leave_status(leave_id, statut, decided_by)


def delete_leave(leave_id):
    return leaves_repository.delete_leave(leave_id)


# --- Lien collaborateur <-> fiche RH -----------------------------------------


def set_employee_hr(external_id, hr_id):
    return leaves_repository.set_employee_hr(external_id, hr_id)
