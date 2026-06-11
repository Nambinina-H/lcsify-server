from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError

from app.audit import audit_service
from app.projects import project_service
from app.projects.schemas import EmployeeRoleIn, ProjectIn, RegisterIn
from app.security.security import (
    check_agent_key,
    get_current_user,
    require_admin,
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
    try:
        created = project_service.create_project(payload)
    except IntegrityError:
        raise HTTPException(status_code=409, detail=_DUPLICATE)
    audit_service.log_event(
        user,
        "project.create",
        f"Projet « {_label(created)} » créé",
        details=payload.model_dump(),
    )
    return created


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


@router.delete("/api/admin/projects/{project_id}")
def delete_project(project_id: int, user=Depends(require_admin)):
    project = project_service.get_project(project_id)
    if project is None or not project_service.delete_project(project_id):
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
    employee_id: str, payload: EmployeeRoleIn, user=Depends(require_admin)
):
    """Definit le role metier (Monteur, ...) d'un collaborateur."""
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
    """L'agent s'annonce (employee_id + nom) -> visible et assignable de suite."""
    return project_service.register_employee(payload)
