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
- Temps réel événementiel : présence poussée *sur changement* + passage hors-ligne explicite et immédiat (`state="offline"`) ; SSE rafraîchi à 1 s

**Fixed**
- Compatibilité PostgreSQL de `/api/details` (ajout de `project` au `GROUP BY`)

## 2026-06-09
**Added**
- Refonte du schéma en vraies entités liées par clés étrangères : `users`, `employees`, `clients`, `projects`, `segments` (+ `TimestampMixin` commun)
- **Comptes managers** (JWT access/refresh + rôles ADMIN/MANAGER) : `/api/auth/login`, `/api/auth/refresh`, `/api/auth/me` ; compte admin créé au démarrage
- Ingestion **get-or-create** : l'agent envoie des noms, le serveur résout/crée le monteur et relie le segment au client/projet existants (contrat agent inchangé)

**Updated**
- Authentification du dashboard : `X-Dashboard-Password` remplacé par `Authorization: Bearer` (écritures réservées aux admins) ; l'agent garde `X-API-Key`
- `report` et `projects` réécrits sur les jointures FK ; horodatages des segments en vrai `DateTime` ; nouvelle baseline Alembic ; `seed_demo.py` adapté aux entités

**Removed**
- Données et schéma plats (segments à colonnes texte, projets à client en chaîne) — reset propre

## 2026-06-10
**Added**
- Endpoint `POST /api/register` (clé agent) : l'agent s'enregistre (employee_id + nom) → monteur **visible et assignable sans attendre d'activité**

**Updated**
- Jeu de démo (`seed_demo.py`) : scénario d'activité courte et fragmentée (test de la frise du calendrier)

## 2026-06-11
**Added**
- **Journal d'audit** : table `audit_logs` + domaine `audit` (router → service → repository) ; événements enregistrés sur connexion, création/modification/suppression de projet, config agents et changement de rôle ; `GET /api/admin/audit` (admin, paginé, **recherche `q`** insensible à la casse + **filtre `action`** + **plage de dates `date_from`/`date_to`**)
- Colonne **`role`** (métier) sur `employees` + `PATCH /api/admin/employees/{id}/role` (admin) ; `role` renvoyé par `GET /api/admin/employees` — migration Alembic `b7c1d2e3f4a5` (appliquée automatiquement au démarrage)
- **Gestion des utilisateurs** (admin) : `GET/POST/PATCH/DELETE /api/admin/users` + `POST /api/admin/users/{id}/password` (créer, changer rôle/statut, réinitialiser le mot de passe, **supprimer**) avec garde-fous (email unique, ≥ 1 admin actif, pas d'auto-verrouillage ni d'auto-suppression) et audit

- `POST /api/auth/verify-password` (compte connecté) : re-confirme le mot de passe avant une action sensible (sans émettre de jeton ni d'événement de connexion)

**Updated**
- **Rôle Manager opérationnel** : création/modification de projet désormais autorisées au **Manager** (`require_manager`) ; suppression de projet, config agents, rôles et utilisateurs restent **réservés à l'admin** (`require_admin`)
