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
- `/api/day-activity` renvoie aussi **client** et **version** des segments (étiquette « Vidéo - client - version » dans la frise du jour)
- Ingestion : **recalage de l'horloge agent** — si l'agent fournit `client_sent_at`, le serveur corrige le décalage de l'horloge du poste (heures d'activité fiables sans dépendre de l'horloge du PC ; seuil 30 s, durées préservées). Rétro-compatible (agents sans ce champ : aucun changement)
- **Permissions par utilisateur (scopes)** : colonne `users.scopes` (migration `c3d4e5f6a7b8`) + module `security/scopes` (`require_scope`) ; au-delà du rôle, on accorde `dashboard:view`, `history:view`, `users:view|manage`, `settings:view|manage`. Endpoints audit/config/users gardés par scope ; `/api/auth/me` et la liste users renvoient `scopes`. **Garde-fous anti-escalade** : seul un admin assigne rôle/scopes ; un non-admin ne gère jamais un compte admin et ne se promeut pas

**Updated**
- **Rôle Manager opérationnel** : création/modification de projet désormais autorisées au **Manager** (`require_manager`) ; suppression de projet, config agents, rôles et utilisateurs restent **réservés à l'admin** (`require_admin`)

## 2026-06-16
**Added**
- Projets : champ dérivé **`is_current`** dans `GET /api/admin/projects` — marque **LE** projet sur lequel chaque collaborateur travaille en dernier (focus actuel, d'après son **segment d'activité le plus récent**). Distingue « En cours » (un seul à la fois) des autres projets assignés qui passent « En attente ». Calculé à la lecture (**aucune migration, rétroactif**) ; jamais vrai pour un projet terminé
