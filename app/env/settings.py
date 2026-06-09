import os

from pydantic_settings import BaseSettings, SettingsConfigDict

# Racine du serveur (dossier server/), calculee a partir de ce fichier.
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


class Settings(BaseSettings):
    """Configuration du serveur.

    Les valeurs sont lues, par ordre de priorite :
      1. variables d'environnement (ex. export AGENT_API_KEY=...)
      2. fichier server/.env
      3. valeurs par defaut ci-dessous
    """

    agent_api_key: str = "CHANGE_ME"
    db_path: str = os.path.join(BASE_DIR, "activity.db")
    # URL de base de donnees. Vide -> SQLite (fichier db_path).
    # Pour PostgreSQL : postgresql+psycopg2://user:pass@host:5432/dbname
    database_url: str = ""
    # Origine du frontend Next.js autorisee par CORS (separer par des virgules
    # pour en autoriser plusieurs).
    frontend_url: str = "http://localhost:3000"

    # --- Authentification des managers (JWT) ---
    jwt_secret: str = "CHANGE_ME_JWT_SECRET"
    jwt_access_ttl_min: int = 30        # duree de vie du token d'acces (minutes)
    jwt_refresh_ttl_days: int = 7       # duree de vie du token de rafraichissement
    # Compte admin cree au demarrage s'il n'existe aucun utilisateur.
    admin_email: str = "admin@gmail.com"
    admin_password: str = "admin"
    admin_name: str = "admin"

    model_config = SettingsConfigDict(
        env_file=os.path.join(BASE_DIR, ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

# Constantes exposees pour le reste du code (retro-compatibilite des imports).
AGENT_API_KEY = settings.agent_api_key
JWT_SECRET = settings.jwt_secret
JWT_ACCESS_TTL_MIN = settings.jwt_access_ttl_min
JWT_REFRESH_TTL_DAYS = settings.jwt_refresh_ttl_days
DB_PATH = settings.db_path
STATIC_DIR = os.path.join(BASE_DIR, "static")
CORS_ORIGINS = [o.strip() for o in settings.frontend_url.split(",") if o.strip()]

# URL effective : celle fournie (ex. Postgres), sinon SQLite sur le fichier local.
SQLITE_URL = f"sqlite:///{DB_PATH.replace(os.sep, '/')}"
_db_url = settings.database_url
# Railway/Heroku fournissent parfois "postgres://" que SQLAlchemy 2.0 refuse.
if _db_url.startswith("postgres://"):
    _db_url = _db_url.replace("postgres://", "postgresql://", 1)
DATABASE_URL = _db_url or SQLITE_URL
