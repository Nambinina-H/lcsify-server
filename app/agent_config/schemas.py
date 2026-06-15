from pydantic import BaseModel, Field


class AgentConfig(BaseModel):
    """Reglages centraux (bornes incluses).

    Les 4 premiers sont appliques aux agents ; `apm_min_active_sec` est un
    reglage d'affichage du tableau de bord (ignore par les agents)."""

    sample_interval_sec: int = Field(5, ge=1, le=3600)
    idle_threshold_sec: int = Field(120, ge=5, le=86400)
    sync_interval_sec: int = Field(60, ge=5, le=3600)
    sync_batch_size: int = Field(500, ge=1, le=5000)
    # Temps actif minimum (cumule sur la periode) avant d'afficher l'APM d'un
    # collaborateur ; en dessous -> "-". 0 = toujours afficher.
    apm_min_active_sec: int = Field(30, ge=0, le=86400)
