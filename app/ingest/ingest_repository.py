from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.database.database import engine
from app.database.database_session import SessionLocal
from app.database.models import Client, Employee, Project, Segment
from app.logging_config import get_logger

logger = get_logger()

# En-deca de ce seuil, c'est la latence reseau normale : on ne touche a rien.
_CLOCK_SKEW_THRESHOLD_SEC = 30

# Tolerance pour ecarter un segment "quasi-identique" a un segment deja
# enregistre (doublon de capture parallele : deux agents lances en meme temps).
_DUP_TOLERANCE = timedelta(seconds=1)


def _insert_stmt():
    """INSERT ... ON CONFLICT DO NOTHING selon le dialecte (ignore les doublons)."""
    return pg_insert if engine.dialect.name == "postgresql" else sqlite_insert


def _parse_dt(value):
    """ISO -> datetime UTC naif (coherent sur SQLite et Postgres)."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _clock_skew(now, client_sent_at):
    """Decalage a appliquer aux horodatages agent pour recaler son horloge sur
    celle (fiable) du serveur. timedelta(0) si non fourni ou negligeable.

    skew > 0 : l'horloge de l'agent RETARDE (on avance ses heures).
    skew < 0 : elle AVANCE (on recule ses heures). On conserve les durees
    (decalage identique applique au debut et a la fin de chaque segment)."""
    sent = _parse_dt(client_sent_at)
    if sent is None:
        return timedelta(0)
    skew = now - sent
    if abs(skew.total_seconds()) < _CLOCK_SKEW_THRESHOLD_SEC:
        return timedelta(0)
    # Arrondi a la seconde : stabilite de la deduplication entre renvois.
    return timedelta(seconds=round(skew.total_seconds()))


def _get_or_create_employee(session, cache, external_id, name):
    """Le monteur est cree automatiquement la 1re fois qu'on le voit (registre)."""
    if external_id in cache:
        return cache[external_id]
    emp = session.execute(
        select(Employee).where(Employee.external_id == external_id)
    ).scalar_one_or_none()
    if emp is None:
        emp = Employee(external_id=external_id, name=name)
        session.add(emp)
        session.flush()  # pour obtenir l'id
    elif name and emp.name != name:
        emp.name = name  # le nom courant fait foi
    cache[external_id] = emp.id
    return emp.id


def _lookup_project(session, client_cache, project_cache, client_name, video, version):
    """Resout le projet existant (client+video+version). Pas de creation auto :
    seuls les projets crees par l'admin comptent. None si pas de correspondance."""
    if not (client_name and video and version):
        return None
    if client_name not in client_cache:
        client_cache[client_name] = session.execute(
            select(Client.id).where(Client.name == client_name)
        ).scalar_one_or_none()
    client_id = client_cache[client_name]
    if client_id is None:
        return None
    key = (client_id, video, version)
    if key not in project_cache:
        project_cache[key] = session.execute(
            select(Project.id).where(
                Project.client_id == client_id,
                Project.video_name == video,
                Project.version == version,
            )
        ).scalar_one_or_none()
    return project_cache[key]


def _filter_near_duplicates(session, rows):
    """Ecarte les segments quasi-identiques a un segment deja enregistre pour le
    meme collaborateur.

    Doublon = meme (employe, app, fenetre, etat) ET memes bornes (debut ET fin)
    a `_DUP_TOLERANCE` pres. Cible les doublons de capture parallele (deux agents
    simultanes reagissent aux memes changements de fenetre -> bornes identiques
    au µs). Sans risque pour les segments consecutifs : l'agent ouvre un nouveau
    segment a chaque changement de cle (app/fenetre/etat), donc deux segments qui
    se suivent different toujours d'au moins un de ces champs.

    Renvoie (rows_a_inserer, nb_ecartes). Les rows sans bornes connues sont
    conservees telles quelles (rien a comparer).
    """
    comparable = [
        r for r in rows
        if r["started_at"] is not None and r["ended_at"] is not None
    ]
    if not comparable:
        return rows, 0

    emp_ids = {r["employee_id"] for r in comparable}
    lo = min(r["started_at"] for r in comparable) - _DUP_TOLERANCE
    hi = max(r["started_at"] for r in comparable) + _DUP_TOLERANCE

    existing = session.execute(
        select(
            Segment.employee_id,
            Segment.app,
            Segment.window_title,
            Segment.state,
            Segment.started_at,
            Segment.ended_at,
        ).where(
            Segment.employee_id.in_(emp_ids),
            Segment.started_at >= lo,
            Segment.started_at <= hi,
        )
    ).all()

    # (employe, app, fenetre, etat) -> liste de (started_at, ended_at)
    index = {}
    for emp, app, title, state, s, e in existing:
        if s is None or e is None:
            continue
        index.setdefault((emp, app, title, state), []).append((s, e))

    tol = _DUP_TOLERANCE.total_seconds()

    def _is_dup(row):
        key = (row["employee_id"], row["app"], row["window_title"], row["state"])
        s, e = row["started_at"], row["ended_at"]
        for es, ee in index.get(key, ()):  # listes courtes (meme cle, proche)
            if (abs((es - s).total_seconds()) <= tol
                    and abs((ee - e).total_seconds()) <= tol):
                return True
        return False

    kept, skipped = [], 0
    for r in rows:
        if r["started_at"] is None or r["ended_at"] is None:
            kept.append(r)
            continue
        if _is_dup(r):
            skipped += 1
            continue
        kept.append(r)
        # Ajoute a l'index : ecarte aussi un doublon present dans le meme lot.
        key = (r["employee_id"], r["app"], r["window_title"], r["state"])
        index.setdefault(key, []).append((r["started_at"], r["ended_at"]))
    return kept, skipped


def insert_segments(events, client_sent_at=None):
    """Insere les segments en resolvant noms -> cles etrangeres (get-or-create).

    L'agent envoie des noms (external_id, client, video, version) ; on les mappe
    aux entites. Doublons ignores. Une erreur de base remonte (-> 500 -> retry).

    Si l'agent fournit `client_sent_at`, on recale ses horodatages sur l'horloge
    du serveur (corrige un PC a l'heure fausse, sans dependre de son horloge).
    """
    if not events:
        return 0

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    skew = _clock_skew(now, client_sent_at)
    if skew:
        logger.warning(
            "Horloge agent recalee de %ss a l'ingestion (%s evenements)",
            int(skew.total_seconds()),
            len(events),
        )

    # Nom le plus recent par monteur (event au end_ts le plus grand).
    latest_name = {}
    for e in events:
        ts = e.end_ts or ""
        if e.employee_name and (
            e.employee_id not in latest_name or ts >= latest_name[e.employee_id][0]
        ):
            latest_name[e.employee_id] = (ts, e.employee_name)

    emp_cache, client_cache, project_cache = {}, {}, {}
    with SessionLocal() as session:
        rows = []
        for e in events:
            name = latest_name.get(e.employee_id, (None, None))[1]
            emp_id = _get_or_create_employee(session, emp_cache, e.employee_id, name)
            project_id = _lookup_project(
                session, client_cache, project_cache, e.client, e.project, e.version
            )
            started_at = _parse_dt(e.start_ts)
            ended_at = _parse_dt(e.end_ts)
            if skew:
                if started_at is not None:
                    started_at += skew
                if ended_at is not None:
                    ended_at += skew
            rows.append({
                "employee_id": emp_id,
                "project_id": project_id,
                "app": e.app,
                "window_title": e.window_title,
                "state": e.state,
                "started_at": started_at,
                "ended_at": ended_at,
                "duration_sec": e.duration_sec,
                "clicks": e.clicks or 0,
                "received_at": now,
            })

        # Garde-fou anti-doublons de capture parallele (deux agents simultanes).
        rows, skipped = _filter_near_duplicates(session, rows)
        if skipped:
            logger.warning(
                "Ingestion : %s segment(s) quasi-doublon(s) ecarte(s).", skipped
            )
        if not rows:
            return 0

        stmt = _insert_stmt()(Segment).values(rows).on_conflict_do_nothing()
        result = session.execute(stmt)
        session.commit()

    return result.rowcount if result.rowcount and result.rowcount > 0 else 0
