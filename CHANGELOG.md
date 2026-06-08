# Changelog

## 2026-06-03
**Added**
- Architecture par domaine (router -> service -> repository)
- Ingestion des événements des agents + tableau de bord (par monteur, projet, application, détail des fenêtres, timeline)
- Champs **client / version** + état **pause**
- Authentification : clé API agent + mot de passe dashboard (en-têtes HTTP)
- Configuration par `.env` (pydantic-settings), logging rotatif, gestion d'erreurs globale, `lifespan`

## 2026-06-04
**Added**
- Base de données via **SQLAlchemy** : SQLite par défaut, **PostgreSQL** si configuré (repli automatique sur SQLite si injoignable)
- Migrations **Alembic** (schéma versionné, appliqué au démarrage)
- Configuration centrale des agents (endpoints lecture par clé API / écriture par mot de passe)
- **CORS** pour le frontend Next.js
- Propagation du nom du monteur sur tout son historique (changement de nom dans l'agent)
- Déploiement Railway : `Procfile` (commande uvicorn) + pin Python 3.12
- Temps réel : présence en mémoire + `POST /api/heartbeat` (agent) + flux SSE `GET /api/live` (dashboard)

**Updated**
- Normalisation des URLs Postgres (`postgres://` -> `postgresql://`) pour Railway/Heroku

**Fixed**
- Compatibilité PostgreSQL de `/api/details` (ajout de `project` au `GROUP BY`)
