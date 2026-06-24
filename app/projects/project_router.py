from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError

from app.audit import audit_service
from app.auth import auth_repository
from app.projects import project_service
from app.projects.schemas import (
    AgentRoleIn,
    EmployeeRoleIn,
    ProjectCompleteIn,
    ProjectIn,
    ProjectPriorityIn,
    ProjectStatusIn,
    RegisterIn,
)
from app.security.scopes import require_scope
from app.security.security import (
    check_agent_key,
    get_current_user,
    require_manager,
)

router = APIRouter()

_DUPLICATE = "Un projet identique (client / video / version) existe deja."


def _label(p: dict) -> str:
    """Libelle court d'un projet pour le journal d'audit."""
    return f"{p['client']} / {p['video_name']} {p['version']}"


# --- Administration (manager connecte ; ecritures reservees admin) -----------


@router.get("/api/admin/projects")
def list_projects(_=Depends(get_current_user)):
    return project_service.list_projects()


@router.post("/api/admin/projects")
def create_project(payload: ProjectIn, user=Depends(require_manager)):
    db_user = auth_repository.get_by_id(user["id"])
    created_by = db_user.name if db_user else None
    try:
        created = project_service.create_project(payload, created_by)
    except IntegrityError:
        raise HTTPException(status_code=409, detail=_DUPLICATE)
    audit_service.log_event(
        user,
        "project.create",
        f"Projet « {_label(created)} » créé",
        details=payload.model_dump(),
    )
    return created


@router.put("/api/admin/projects/priority")
def set_projects_priority(payload: ProjectPriorityIn, user=Depends(require_manager)):
    """Manager : enregistre l'ordre de priorite des projets d'un collaborateur
    (priority = 1, 2, 3... dans l'ordre fourni). Declaree AVANT la route
    `{project_id}` pour ne pas etre captee par celle-ci."""
    result = project_service.set_priorities(payload.ordered_ids)
    audit_service.log_event(
        user, "project.priority", "Priorité des projets mise à jour"
    )
    return result


@router.put("/api/admin/projects/{project_id}")
def update_project(project_id: int, payload: ProjectIn, user=Depends(require_manager)):
    try:
        updated = project_service.update_project(project_id, payload)
    except IntegrityError:
        raise HTTPException(status_code=409, detail=_DUPLICATE)
    if updated is None:
        raise HTTPException(status_code=404, detail="Projet introuvable")
    audit_service.log_event(
        user,
        "project.update",
        f"Projet « {_label(updated)} » modifié",
        details=payload.model_dump(),
    )
    return updated


@router.patch("/api/admin/projects/{project_id}/status")
def set_project_status(
    project_id: int, payload: ProjectStatusIn, user=Depends(require_manager)
):
    """Manager : marque un projet « termine » ou le « rouvre »."""
    if payload.status not in ("en_cours", "termine"):
        raise HTTPException(status_code=422, detail="Statut invalide")
    db_user = auth_repository.get_by_id(user["id"])
    by = db_user.name if db_user else None
    updated = project_service.set_project_status(project_id, payload.status, by)
    if updated is None:
        raise HTTPException(status_code=404, detail="Projet introuvable")
    audit_service.log_event(
        user,
        "project.status",
        f"Projet « {_label(updated)} » "
        + ("marqué terminé" if payload.status == "termine" else "rouvert"),
    )
    return updated


@router.delete("/api/admin/projects/{project_id}")
def delete_project(project_id: int, user=Depends(require_scope("projects", "manage"))):
    project = project_service.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Projet introuvable")
    # Garde-fou : on ne supprime pas un projet EN COURS qui a un temps prevu
    # (sa suppression detacherait le temps enregistre -> « Sans projet »). Il
    # faut d'abord le marquer « termine ». Exception : un projet « Non estime »
    # (sans temps prevu) reste supprimable directement.
    if project.get("status") != "termine" and (
        project.get("estimated_duration_sec") or 0
    ) > 0:
        raise HTTPException(
            status_code=409,
            detail="Projet en cours : marquez-le « Terminé » avant de le supprimer.",
        )
    if not project_service.delete_project(project_id):
        raise HTTPException(status_code=404, detail="Projet introuvable")
    audit_service.log_event(
        user, "project.delete", f"Projet « {_label(project)} » supprimé"
    )
    return {"status": "ok"}


@router.get("/api/admin/employees")
def list_employees(_=Depends(get_current_user)):
    return project_service.list_employees()


@router.patch("/api/admin/employees/{employee_id}/role")
def set_employee_role(
    employee_id: str,
    payload: EmployeeRoleIn,
    user=Depends(require_scope("collaborators", "manage")),
):
    """Definit le role metier (Monteur, ...) d'un collaborateur (admin ou scope
    `collaborators:manage`)."""
    updated = project_service.set_employee_role(employee_id, payload.role)
    if updated is None:
        raise HTTPException(status_code=404, detail="Collaborateur introuvable")
    audit_service.log_event(
        user,
        "employee.role",
        f"Rôle de {updated['employee_name']} : {updated['role'] or '(aucun)'}",
    )
    return updated


# --- Agent (cle API) ---------------------------------------------------------


@router.get("/api/assigned-projects")
def assigned_projects(employee_id: str, _=Depends(check_agent_key)):
    return {"projects": project_service.list_for_employee(employee_id)}


@router.post("/api/register")
def register(payload: RegisterIn, _=Depends(check_agent_key)):
    """L'agent s'annonce (employee_id + nom) -> visible et assignable de suite.
    La reponse inclut le `role` courant (affiche dans l'agent)."""
    return project_service.register_employee(payload)


@router.post("/api/agent/role")
def agent_set_role(payload: AgentRoleIn, _=Depends(check_agent_key)):
    """L'agent definit le role metier du collaborateur (ecran Parametres). Meme
    champ que la page Collaborateurs (un manager peut aussi le modifier)."""
    updated = project_service.set_employee_role(payload.employee_id, payload.role)
    if updated is None:
        raise HTTPException(status_code=404, detail="Collaborateur introuvable")
    return updated


@router.post("/api/agent/project-complete")
def agent_project_complete(payload: ProjectCompleteIn, _=Depends(check_agent_key)):
    """L'agent (monteur) marque un de SES projets assignes comme termine."""
    result = project_service.complete_project_for_employee(
        payload.employee_id, payload.project_id
    )
    if result == "not_found":
        raise HTTPException(status_code=404, detail="Projet introuvable")
    if result == "forbidden":
        raise HTTPException(
            status_code=403, detail="Projet non assigné à ce collaborateur"
        )
    return result
