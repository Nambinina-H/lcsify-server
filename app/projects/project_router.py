from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError

from app.projects import project_service
from app.projects.schemas import ProjectIn
from app.security.security import check_agent_key, get_current_user, require_admin

router = APIRouter()

_DUPLICATE = "Un projet identique (client / video / version) existe deja."


# --- Administration (manager connecte ; ecritures reservees admin) -----------


@router.get("/api/admin/projects")
def list_projects(_=Depends(get_current_user)):
    return project_service.list_projects()


@router.post("/api/admin/projects")
def create_project(payload: ProjectIn, _=Depends(require_admin)):
    try:
        return project_service.create_project(payload)
    except IntegrityError:
        raise HTTPException(status_code=409, detail=_DUPLICATE)


@router.put("/api/admin/projects/{project_id}")
def update_project(project_id: int, payload: ProjectIn, _=Depends(require_admin)):
    try:
        updated = project_service.update_project(project_id, payload)
    except IntegrityError:
        raise HTTPException(status_code=409, detail=_DUPLICATE)
    if updated is None:
        raise HTTPException(status_code=404, detail="Projet introuvable")
    return updated


@router.delete("/api/admin/projects/{project_id}")
def delete_project(project_id: int, _=Depends(require_admin)):
    if not project_service.delete_project(project_id):
        raise HTTPException(status_code=404, detail="Projet introuvable")
    return {"status": "ok"}


@router.get("/api/admin/employees")
def list_employees(_=Depends(get_current_user)):
    return project_service.list_employees()


# --- Agent (cle API) ---------------------------------------------------------


@router.get("/api/assigned-projects")
def assigned_projects(employee_id: str, _=Depends(check_agent_key)):
    return {"projects": project_service.list_for_employee(employee_id)}
