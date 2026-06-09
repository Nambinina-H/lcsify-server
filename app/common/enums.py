from enum import Enum


class StateEnum(str, Enum):
    """Etats possibles d'un segment d'activite."""

    ACTIVE = "active"
    IDLE = "idle"
    PAUSED = "paused"


class RoleEnum(str, Enum):
    """Roles des comptes manager du dashboard."""

    ADMIN = "admin"      # acces complet (gestion projets, config)
    MANAGER = "manager"  # lecture seule du dashboard
