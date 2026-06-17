from pydantic import BaseModel, Field


class SpaceIn(BaseModel):
    """Creation / modification d'un espace (categorie de collaborateurs)."""

    name: str = Field(min_length=1, max_length=120)
    color: str = Field(default="#1d4ed8", max_length=20)
    icon: str = Field(default="grid", max_length=40)
    # external_id des collaborateurs membres (un collaborateur = un seul espace :
    # l'affecter ici le retire de son espace precedent).
    member_ids: list[str] = Field(default_factory=list)