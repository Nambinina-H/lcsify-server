from enum import Enum


class StateEnum(str, Enum):
    """Etats possibles d'un segment d'activite."""

    ACTIVE = "active"
    IDLE = "idle"
    PAUSED = "paused"


class RoleEnum(str, Enum):
    """Roles des comptes manager du dashboard."""

    ADMIN = "admin"      # acces complet (dashboard, config, utilisateurs)
    MANAGER = "manager"  # projets/collaborateurs/calendrier (assigne les projets)
