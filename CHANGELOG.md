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

## 2026-06-17
**Added**
- **Espaces (catégories de collaborateurs)** : nouvelle table `spaces` + colonne `employees.space_id` (migration `b8c9d0e1f2a3`, additive et non destructive). Domaine `spaces` : `GET/POST/PUT/DELETE /api/admin/spaces` (manager) — chaque espace a un nom, une couleur, une icône et des membres. **Un collaborateur appartient à un seul espace** (l'affecter ailleurs le retire du précédent) ; supprimer un espace **détache** ses membres sans toucher au collaborateur ni à son historique. Le dashboard se filtre par espace : paramètre optionnel **`space_id`** sur `/api/summary`, `/api/projects`, `/api/apps`, `/api/details`, `/api/calendar`, `/api/day-activity` (absent = tous). `GET /api/admin/employees` renvoie aussi `space_id`. Rétro-compatible : sans `space_id`, comportement inchangé
- **Priorisation des projets** : colonne `priority` sur `projects` (migration `a7b8c9d0e1f2`) + `PUT /api/admin/projects/priority` (manager) pour enregistrer l'ordre des projets d'un collaborateur (priority = 1, 2, 3…). `GET /api/assigned-projects` et la liste admin renvoient les projets **triés par priorité** ; audit `project.priority`
- `GET /api/assigned-projects` renvoie aussi **`spent_sec`** par projet (temps actif = ce qu'affiche le dashboard) : l'agent cale son compteur sur le serveur, fin des écarts agent/plateforme
- **Scope `collaborators:manage`** : l'édition du rôle métier d'un collaborateur (`PATCH /api/admin/employees/{id}/role`) n'est plus réservée à l'admin — elle est **accordable à un manager** via ce scope (admin garde tout). Refus (403) sans le scope
- **Rôle depuis l'agent** : `POST /api/agent/role` (clé agent) permet au collaborateur de définir son rôle métier depuis l'écran Paramètres de l'agent — **même champ** que la page Collaborateurs. `POST /api/register` renvoie désormais le **`role`** courant (l'agent l'affiche ; il ne l'écrase jamais à la synchro)
- **Migration d'identité dans `POST /api/register`** : champ optionnel **`previous_id`** — si l'ancien identifiant (machine) existe encore et que le nouveau (`nom@PC`) n'existe pas, le serveur **renomme** l'enregistrement (les segments/projets, liés par l'id interne, suivent → aucune perte). Prépare l'identité **par personne** (agent v1.0.8). Un agent qui se (re)connecte est **réactivé** (`is_active`). Rétro-compatible : sans `previous_id`, comportement inchangé

**Fixed**
- **Doublons de collaborateur (course de migration v1.0.8)** : `POST /api/register` **fusionne** désormais l'ancien identifiant dans le nouveau quand **les deux existent** (la migration `nom@PC` pouvait créer un doublon si un segment/heartbeat créait le nouveau record avant le renommage). Les segments/projets sont déplacés sous `nom@PC`, les segments en double supprimés, l'ancien record effacé — **aucune perte**. **Auto-réparation** : chaque agent en ligne fusionne son doublon à son prochain `register` (~1 min), sans mise à jour de l'agent
- **Garde-fou anti-doublons à l'ingestion** : un segment **quasi-identique** à un segment déjà enregistré pour le même collaborateur (même app/fenêtre/état **et** mêmes bornes début+fin à ~1 s près) est désormais **écarté**. Corrige le **temps gonflé** quand deux agents tournaient en parallèle sur un même poste (capture en double, horodatages décalés de quelques µs que la contrainte d'unicité ne voyait pas). Sans risque pour les segments consécutifs (l'agent ouvre un nouveau segment à chaque changement d'app/fenêtre/état). N'affecte **que les nouvelles ingestions** (l'historique n'est pas modifié)

## 2026-06-18
**Added**
- **Export Excel du calendrier** : `GET /api/calendar/export?year&month&space_id` (manager) renvoie un **`.xlsx`** — grille hebdo type Clockify pour le mois : un bloc **par agent** (lignes = sa plage horaire perso détectée, début d'activité → +9h, en **heure locale UTC+3**), colonnes **Lun→Ven regroupées par semaine** ; chaque case liste **tous les projets** capturés cette heure-là, **couleur = version dominante** (V1/V2/V3/Autres) + **rouge si dépassement**, fusion des heures consécutives identiques. Statuts manuels (congé/attente…) non gérés → cases vides. Dépendance : `openpyxl`
- Export calendrier — **mise en forme** : semaines numérotées **« Semaine 1, 2… »** (relatif au mois), **colonne vide** entre les semaines, **séparateur épais** entre agents, palette **V1 violet / V2 bleu / V3 rose / Autres gris clair / Dépassement rouge**, **légende verticale** avec titre centré

## 2026-06-24
**Added**
- **Garde-fou anti-suppression de projet** : `DELETE /api/admin/projects/{id}` refuse désormais (**409**) la suppression d'un projet **en cours qui a un temps prévu** — il faut d'abord le marquer **« terminé »** (sinon le temps déjà enregistré serait détaché → « Sans projet »). Exceptions : un projet **terminé** ou **« Non estimé »** (sans temps prévu) reste supprimable directement

## 2026-06-29
**Added**
- **Gestion des congés** : nouvelles tables `hr_collaborateurs` (registre RH) et `leaves` (migrations `c9d0e1f2a3b4` et `d0e1f2a3b4c5`, **additives**) + colonne `employees.hr_collaborateur_id` (lien collaborateur ↔ fiche RH). Domaine `leaves` : `GET/POST/PUT/DELETE /api/admin/hr-collaborateurs` (+ import du fichier RH `.xlsx`/`.csv` via `POST .../import`), `GET/POST/PUT/DELETE /api/admin/leaves`, `PATCH /api/admin/leaves/{id}/status` (validation : en attente → approuvé/refusé, avec traçabilité du décideur `decided_by`/`decided_at`), et `PATCH /api/admin/employees/{id}/hr-link`. **Solde calculé à la lecture** : solde initial + 2,5 j par fin de mois écoulée depuis la date de référence − congés payés approuvés ; décompte en **jours calendaires** (week-ends inclus). Nouveau scope **`leaves:manage`**. `GET /api/admin/employees` renvoie aussi `hr_collaborateur_id`/`hr_matricule`. Dépendance ajoutée : **`python-multipart`** (upload). Rétro-compatible : sans le scope l'accès est refusé ; l'ingestion et le contrat agent sont inchangés

**Updated**
- Congés : champ **`validateur`** (désigné à la création, saisi au formulaire) ajouté sur `leaves` — migration `e1f2a3b4c5d6` (additive). Affiché dans le tableau ; distinct de `decided_by` (qui valide réellement le congé, tracé via l'audit `leave.status`)

## 2026-07-01
**Added**
- Export calendrier — **format « Récap »** : `GET /api/calendar/export?…&format=recap` (manager) renvoie un `.xlsx` **par collaborateur** listant ses **projets travaillés** sur la plage, avec **Temps prévu** / **Temps actuel** (temps actif cumulé, identique à la page Projets) / **Temps restant** (= prévu − actuel, rouge si dépassé). Nouveau paramètre **`format=grid|recap`** (défaut `grid` ; la grille horaire reste inchangée)

**Updated**
- Export Excel du calendrier : l'endpoint passe de `year&month&space_id` à **`GET /api/calendar/export?date_from&date_to&employee_ids`** (manager) — export sur une **plage de dates libre** et pour une **liste de collaborateurs** choisis (external_id séparés par des virgules ; vide = tous). Dates invalides ou fin < début → **422**
- Export calendrier : on compte désormais la **présence** sur le projet = **actif + inactif (idle)** ; la **pause volontaire** reste exclue (case vide). Le dépassement (rouge) reste basé sur l'actif
- Export calendrier — **commentaire par bloc-projet** (au survol dans Excel/Google Sheets) : **Début / Fin / Total** (1er début, dernière fin, temps total de présence), une fois par projet-jour
- Export calendrier — mise en forme : colonne **Heure** en **nombre seul, centré et gras** (sans « h ») ; **titre « Légende » retiré** (case conservée)
