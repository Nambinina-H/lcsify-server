from fastapi import APIRouter, Depends

from app.agent_config import config_service
from app.agent_config.schemas import AgentConfig
from app.audit import audit_service
from app.security.scopes import require_scope
from app.security.security import check_agent_key

router = APIRouter()


@router.get("/api/agent-config")
def agent_config(_=Depends(check_agent_key)):
    """Lue par les agents (cle API) : la config a appliquer + top de MAJ."""
    return config_service.get_agent_payload()


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


@router.post("/api/admin/agents/update-now")
def admin_update_now(user=Depends(require_scope("settings", "manage"))):
    """Declenche une MAJ immediate de la flotte : les agents ouverts telechargent
    la derniere version a leur prochaine lecture de config (~60 s), puis proposent
    le redemarrage. Sans effet sur un agent deja a jour."""
    signal = config_service.bump_update_signal()
    audit_service.log_event(
        user,
        "agents.update_now",
        "Mise à jour immédiate des agents déclenchée",
    )
    return {"update_signal": signal}
