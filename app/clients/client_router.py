from fastapi import APIRouter, Depends, HTTPException

from app.audit import audit_service
from app.clients import client_service
from app.clients.schemas import ClientIn
from app.security.security import get_current_user, require_admin, require_manager

router = APIRouter()

_DUPLICATE = "Un client portant ce nom existe deja."


@router.get("/api/admin/clients")
def list_clients(_=Depends(get_current_user)):
    return client_service.list_clients()


@router.post("/api/admin/clients")
def create_client(payload: ClientIn, user=Depends(require_manager)):
    created = client_service.create_client(payload.name)
    if created is None:
        raise HTTPException(status_code=409, detail=_DUPLICATE)
    audit_service.log_event(user, "client.create", f"Client « {created['name']} » créé")
    return created


@router.patch("/api/admin/clients/{client_id}")
def rename_client(client_id: int, payload: ClientIn, user=Depends(require_manager)):
    result = client_service.rename_client(client_id, payload.name)
    if result == "not_found":
        raise HTTPException(status_code=404, detail="Client introuvable")
    if result == "duplicate":
        raise HTTPException(status_code=409, detail=_DUPLICATE)
    audit_service.log_event(user, "client.rename", f"Client renommé en « {result['name']} »")
    return result


@router.delete("/api/admin/clients/{client_id}")
def delete_client(client_id: int, user=Depends(require_admin)):
    result = client_service.delete_client(client_id)
    if result == "not_found":
        raise HTTPException(status_code=404, detail="Client introuvable")
    if result == "has_projects":
        raise HTTPException(
            status_code=409,
            detail="Ce client a des projets : supprime ou réassigne-les d'abord.",
        )
    audit_service.log_event(user, "client.delete", f"Client « {result['name']} » supprimé")
    return {"status": "ok"}