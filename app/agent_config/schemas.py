from pydantic import BaseModel, Field


class AgentConfig(BaseModel):
    """Reglages operationnels appliques a tous les agents (bornes incluses)."""

    sample_interval_sec: int = Field(5, ge=1, le=3600)
    idle_threshold_sec: int = Field(120, ge=5, le=86400)
    sync_interval_sec: int = Field(60, ge=5, le=3600)
    sync_batch_size: int = Field(500, ge=1, le=5000)
