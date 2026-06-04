from enum import Enum


class StateEnum(str, Enum):
    """Etats possibles d'un segment d'activite."""

    ACTIVE = "active"
    IDLE = "idle"
    PAUSED = "paused"
