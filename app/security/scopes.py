"""Permissions additionnelles par utilisateur (au-dela du role).

Un scope = "domaine:niveau" (niveau : view | manage ; manage implique view).
Les ADMIN ont tout, implicitement. Les MANAGER n'ont que les scopes accordes.
"""
import json

from fastapi import Depends, HTTPException

from app.common.enums import RoleEnum
from app.security.security import get_current_user

# Domaines accordables. Certains sont lecture seule, d'autres ecriture seule.
DOMAINS = (
    "dashboard", "history", "users", "settings",
    "projects", "clients", "collaborators", "leaves",
)
_VIEW_ONLY = ("dashboard", "history")        # seulement :view (la page se voit)
# seulement :manage (ex. suppression, ou edition du role des collaborateurs)
_MANAGE_ONLY = ("projects", "clients", "collaborators", "leaves")


def _allowed():
    allowed = set()
    for d in DOMAINS:
        if d not in _MANAGE_ONLY:
            allowed.add(f"{d}:view")
        if d not in _VIEW_ONLY:
            allowed.add(f"{d}:manage")
    return allowed


ALLOWED_SCOPES = _allowed()


def parse_scopes(raw):
    """Texte JSON -> liste de scopes valides. Tolerant (jamais d'erreur)."""
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return []
    if not isinstance(data, list):
        return []
    return [s for s in data if s in ALLOWED_SCOPES]


def clean_scopes(values):
    """Ne garde que des scopes valides, sans doublon (assignation admin)."""
    if not isinstance(values, list):
        return []
    out = []
    for v in values:
        if v in ALLOWED_SCOPES and v not in out:
            out.append(v)
    return out


def _granted(scopes, domain, level):
    if f"{domain}:manage" in scopes:
        return True  # ecriture implique lecture
    return level == "view" and f"{domain}:view" in scopes


def has_scope(user_row, domain, level) -> bool:
    """user_row : objet User (BDD). Admin actif -> toujours vrai."""
    if user_row is None or not user_row.is_active:
        return False
    if user_row.role == RoleEnum.ADMIN.value:
        return True
    return _granted(parse_scopes(user_row.scopes), domain, level)


def require_scope(domain: str, level: str):
    """Dependance FastAPI : admin OU possede le scope `domaine:niveau`."""

    def dep(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") == RoleEnum.ADMIN.value:
            return user
        # Import local : evite un cycle scopes <-> auth_repository.
        from app.auth import auth_repository

        if not has_scope(auth_repository.get_by_id(user["id"]), domain, level):
            raise HTTPException(status_code=403, detail="Acces refuse")
        return user

    return dep
