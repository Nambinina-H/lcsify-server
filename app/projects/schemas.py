from pydantic import BaseModel, Field


class ProjectIn(BaseModel):
    """Donnees d'un projet (creation / modification)."""

    client: str = Field(min_length=1)
    video_name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    estimated_duration_sec: int = Field(0, ge=0)
    assigned_employee_id: str = ""
    assigned_employee_name: str = ""
