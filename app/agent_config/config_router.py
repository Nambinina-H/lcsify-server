from fastapi import APIRouter, Depends

from app.agent_config import config_service
from app.agent_config.schemas import AgentConfig
from app.audit import audit_service
from app.security.scopes import require_scope
from app.security.security import check_agent_key

router = APIRouter()


@router.get("/api/agent-config")
def agent_config(_=Depends(check_agent_key)):
    """Lue par les agents (cle API) : la config a appliquer."""
    return config_service.get_config()


@router.get("/api/admin/config")
def admin_get_config(_=Depends(require_scope("settings", "view"))):
    """Lue par le dashboard : admin ou scope settings:view."""
    return config_service.get_config()


@router.put("/api/admin/config")
def admin_put_config(payload: AgentConfig, user=Depends(require_scope("settings", "manage"))):
    """Modifiee par un admin ou un scope settings:manage. Bornes validees."""
    result = config_service.update_config(payload)
    audit_service.log_event(
        user,
        "config.update",
        "Configuration des agents modifiée",
        details=payload.model_dump(),
    )
    return result
