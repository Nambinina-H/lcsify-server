from pydantic import BaseModel, Field


class ProjectIn(BaseModel):
    """Donnees d'un projet (creation / modification)."""

    client: str = Field(min_length=1)
    video_name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    estimated_duration_sec: int = Field(0, ge=0)
    assigned_employee_id: str = ""
    assigned_employee_name: str = ""


class EmployeeRoleIn(BaseModel):
    """Role metier d'un collaborateur (ex. Monteur), modifiable par un admin."""

    role: str | None = None


class RegisterIn(BaseModel):
    """Annonce d'un monteur par l'agent : se fait connaitre de la plateforme
    (visible + assignable) sans attendre d'activite."""

    employee_id: str = Field(min_length=1)
    employee_name: str = ""
