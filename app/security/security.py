import secrets

from fastapi import Header, HTTPException

from app.env.settings import AGENT_API_KEY, DASH_PASSWORD


def check_agent_key(x_api_key: str = Header(None)):
    if not x_api_key or not secrets.compare_digest(x_api_key, AGENT_API_KEY):
        raise HTTPException(status_code=401, detail="Cle API invalide")


def check_dashboard(x_dashboard_password: str = Header(None)):
    # Le mot de passe transite par un en-tete HTTP (jamais dans l'URL : sinon il
    # finirait dans les logs d'acces, l'historique du navigateur et les proxys).
    if not x_dashboard_password or not secrets.compare_digest(
        x_dashboard_password, DASH_PASSWORD
    ):
        raise HTTPException(status_code=401, detail="Mot de passe invalide")
