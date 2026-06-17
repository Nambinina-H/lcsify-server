from fastapi import APIRouter, Depends, HTTPException

from app.audit import audit_service
from app.security.security import get_current_user, require_manager
from app.spaces import space_service
from app.spaces.schemas import SpaceIn

router = APIRouter()


@router.get("/api/admin/spaces")
def list_spaces(_=Depends(get_current_user)):
    """Liste des espaces (categories de collaborateurs) + nombre de membres."""
    return space_service.list_spaces()


@router.post("/api/admin/spaces")
def create_space(payload: SpaceIn, user=Depends(require_manager)):
    created = space_service.create_space(payload)
    audit_service.log_event(
        user, "space.create", f"Espace « {created['name']} » créé"
    )
    return created


@router.put("/api/admin/spaces/{space_id}")
def update_space(space_id: int, payload: SpaceIn, user=Depends(require_manager)):
    updated = space_service.update_space(space_id, payload)
    if updated is None:
        raise HTTPException(status_code=404, detail="Espace introuvable")
    audit_service.log_event(
        user, "space.update", f"Espace « {updated['name']} » modifié"
    )
    return updated


@router.delete("/api/admin/spaces/{space_id}")
def delete_space(space_id: int, user=Depends(require_manager)):
    deleted = space_service.delete_space(space_id)
    if deleted is None:
        raise HTTPException(status_code=404, detail="Espace introuvable")
    audit_service.log_event(
        user, "space.delete", f"Espace « {deleted['name']} » supprimé"
    )
    return {"status": "ok"}