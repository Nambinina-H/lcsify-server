from typing import Optional

from pydantic import BaseModel


class Heartbeat(BaseModel):
    """État courant léger envoyé fréquemment par l'agent (présence temps réel)."""

    employee_id: str
    employee_name: Optional[str] = None
    client: Optional[str] = None
    project: Optional[str] = None
    version: Optional[str] = None
    app: Optional[str] = None
    window_title: Optional[str] = None
    state: Optional[str] = None
    agent_version: Optional[str] = None  # version de l'agent (pour l'afficher)
