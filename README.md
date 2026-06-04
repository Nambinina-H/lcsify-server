# LCSify — Serveur (API)

Serveur central du suivi d'activité des monteurs. Il **reçoit** les événements
des agents, les range en base, calcule des **agrégats** et expose une **API JSON**
consommée par le dashboard Next.js.

> L'agent et le frontend sont des projets séparés. Tout passe par HTTP.

## Stack
FastAPI · SQLAlchemy 2.0 · Alembic · pydantic-settings · SQLite/PostgreSQL.
Architecture **par domaine** : `router -> service -> repository`.

## Structure
```
app/
  main.py              # wiring (lifespan, routers, CORS, handlers d'erreurs)
  env/settings.py      # configuration via .env (pydantic-settings)
  database/            # engine SQLAlchemy + modeles + migrate (Alembic)
  security/            # cle agent / mot de passe dashboard (en-tetes)
  common/              # enums + handlers d'erreurs
  ingest/              # POST /api/events (reception des agents)
  report/              # GET /api/summary, /projects, /apps, /details, /timeline
  agent_config/        # config centrale des agents
  dashboard/           # sert l'ancien dashboard HTML (/)
alembic/               # migrations de schema
```

## Configuration (.env)
Crée un fichier `.env` (jamais versionné) :
```bash
AGENT_API_KEY=une-cle-secrete-partagee-avec-les-agents
DASH_PASSWORD=mot-de-passe-du-dashboard
FRONTEND_URL=http://localhost:3000
# Base : SQLite par defaut. Pour PostgreSQL :
# DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/lcsify
```

| Variable | Rôle | Défaut |
|---|---|---|
| `AGENT_API_KEY` | Clé partagée avec les agents | `CHANGE_ME` |
| `DASH_PASSWORD` | Mot de passe du dashboard | `admin` |
| `DATABASE_URL` | URL Postgres (vide = SQLite) | _(vide)_ |
| `FRONTEND_URL` | Origine(s) autorisée(s) par CORS | `http://localhost:3000` |

## Base de données
SQLAlchemy : **SQLite** par défaut (zéro config), ou **PostgreSQL** via `DATABASE_URL`.
Si Postgres est injoignable au démarrage, repli automatique sur SQLite.
Les **migrations Alembic** sont appliquées automatiquement au lancement.

Après avoir modifié un modèle (`app/database/models.py`) :
```bash
alembic revision --autogenerate -m "description"
```

## Lancement
```bash
python -m venv venv
venv\Scripts\activate            # Linux/Mac : source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
> Si `uvicorn` n'est pas reconnu : `python -m uvicorn app.main:app --port 8000`.

Données de démo (serveur lancé) : `python simulate.py` (utilise la clé `test-key`).

## Qualité (pre-commit)
```bash
pip install -r requirements.txt   # inclut ruff + pre-commit
pre-commit install                # hooks : ruff, gitleaks, ...
ruff check app                    # lint seul
```

## Déploiement (Railway)
Définis les variables d'environnement (`DATABASE_URL` fournie par Railway,
`AGENT_API_KEY`, `DASH_PASSWORD`, `FRONTEND_URL` = domaine du front). Au démarrage,
les migrations créent le schéma automatiquement.
