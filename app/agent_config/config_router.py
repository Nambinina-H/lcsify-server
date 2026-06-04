from fastapi import APIRouter, Depends

from app.agent_config import config_service
from app.agent_config.schemas import AgentConfig
from app.security.security import check_agent_key, check_dashboard

router = APIRouter()


@router.get("/api/agent-config")
def agent_config(_=Depends(check_agent_key)):
    """Lue par les agents (cle API) : la config a appliquer."""
    return config_service.get_config()


@router.get("/api/admin/config")
def admin_get_config(_=Depends(check_dashboard)):
    """Lue par le dashboard (mot de passe) : la config courante a editer."""
    return config_service.get_config()


@router.put("/api/admin/config")
def admin_put_config(payload: AgentConfig, _=Depends(check_dashboard)):
    """Modifiee par le dashboard (mot de passe). Bornes validees par le schema."""
    return config_service.update_config(payload)
