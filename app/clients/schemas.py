from pydantic import BaseModel, Field


class ClientIn(BaseModel):
    """Nom d'un client (creation / renommage)."""

    name: str = Field(min_length=1)