from fastapi import APIRouter, Depends

from app.agent_config import config_service
from app.agent_config.schemas import AgentConfig
from app.audit import audit_service
from app.security.security import check_agent_key, get_current_user, require_admin

router = APIRouter()


@router.get("/api/agent-config")
def agent_config(_=Depends(check_agent_key)):
    """Lue par les agents (cle API) : la config a appliquer."""
    return config_service.get_config()


@router.get("/api/admin/config")
def admin_get_config(_=Depends(get_current_user)):
    """Lue par le dashboard (manager connecte) : la config courante a editer."""
    return config_service.get_config()


@router.put("/api/admin/config")
def admin_put_config(payload: AgentConfig, user=Depends(require_admin)):
    """Modifiee par un admin. Bornes validees par le schema."""
    result = config_service.update_config(payload)
    audit_service.log_event(
        user,
        "config.update",
        "Configuration des agents modifiée",
        details=payload.model_dump(),
    )
    return result
