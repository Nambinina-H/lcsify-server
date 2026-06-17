from datetime import datetime, timedelta, timezone

from app.agent_config import config_service
from app.report import report_repository


def _range(days, date_from, date_to):
    """Bornes en datetime UTC naif (coherent avec le stockage des segments)."""
    if date_from and date_to:
        lo = datetime.fromisoformat(date_from)
        hi = datetime.fromisoformat(date_to + "T23:59:59")
        return lo, hi
    end = datetime.now(timezone.utc).replace(tzinfo=None)
    return end - timedelta(days=days), end


def _iso(dt):
    """datetime UTC naif -> ISO avec offset (le front l'interprete en UTC)."""
    return dt.replace(tzinfo=timezone.utc).isoformat() if dt else None


# Defaut si non configure : en-deca de ce temps actif (cumule sur la periode),
# l'APM est trop instable pour etre affiche (-> null). Reglable dans Parametres.
_APM_DEFAULT_MIN_ACTIVE_SEC = 30


def summary(days, date_from, date_to, space_id=None):
    lo, hi = _range(days, date_from, date_to)
    rows = report_repository.fetch_summary_totals(lo, hi, space_id)
    current = {c["employee_id"]: c for c in report_repository.fetch_current_activity()}
    apm_min_active = config_service.get_config().get(
        "apm_min_active_sec", _APM_DEFAULT_MIN_ACTIVE_SEC
    )

    result = []
    for r in rows:
        active = r["active_sec"] or 0
        idle = r["idle_sec"] or 0
        paused = r["paused_sec"] or 0
        clicks = r["clicks"] or 0
        # La pause n'est ni active ni inactive : exclue du taux d'activite.
        total = active + idle
        # APM = clics / minutes actives (intensite d'interaction, pas un score
        # de productivite). Null si trop peu d'actif pour etre fiable.
        apm = round(clicks / (active / 60), 1) if active >= apm_min_active else None
        cur = current.get(r["employee_id"])
        result.append({
            "employee_id": r["employee_id"],
            "employee_name": r["employee_name"] or r["employee_id"],
            "active_sec": active,
            "idle_sec": idle,
            "paused_sec": paused,
            "clicks": clicks,
            "apm": apm,
            "activity_rate": round(100 * active / total, 1) if total else 0,
            "last_seen": _iso(r["last_seen"]),
            "current_app": cur["app"] if cur else None,
            "current_title": cur["window_title"] if cur else None,
            "current_project": cur["project"] if cur else None,
            "current_state": cur["state"] if cur else None,
        })
    return {"range": {"from": _iso(lo), "to": _iso(hi)}, "employees": result}


def projects(days, date_from, date_to, employee_id, space_id=None):
    lo, hi = _range(days, date_from, date_to)
    rows = report_repository.fetch_projects(lo, hi, employee_id, space_id)
    return {"projects": [dict(r) for r in rows]}


def apps(days, date_from, date_to, employee_id, space_id=None):
    lo, hi = _range(days, date_from, date_to)
    rows = report_repository.fetch_apps(lo, hi, employee_id, space_id)
    return {"apps": [dict(r) for r in rows]}


def details(days, date_from, date_to, employee_id, space_id=None):
    lo, hi = _range(days, date_from, date_to)
    rows = report_repository.fetch_details(lo, hi, employee_id, space_id)
    return {"details": [dict(r) for r in rows]}


def timeline(employee_id, days, date_from, date_to):
    lo, hi = _range(days, date_from, date_to)
    rows = report_repository.fetch_timeline(employee_id, lo, hi)
    segments = []
    for r in rows:
        d = dict(r)
        d["start_ts"] = _iso(d["start_ts"])
        d["end_ts"] = _iso(d["end_ts"])
        segments.append(d)
    return {"segments": segments}


def project_report(project_id):
    """Analytique d'un projet : avancement, cumul par jour, par monteur, par app."""
    meta = report_repository.fetch_project_meta(project_id)
    if meta is None:
        return None
    daily = [
        {"day": str(r["day"]), "active_sec": r["active_sec"] or 0}
        for r in report_repository.fetch_project_daily(project_id)
        if (r["active_sec"] or 0) > 0
    ]
    spent = sum(d["active_sec"] for d in daily)
    by_employee = [
        {"employee_name": r["employee_name"] or "?", "active_sec": r["active_sec"] or 0}
        for r in report_repository.fetch_project_by_employee(project_id)
    ]
    by_app = [
        {"app": r["app"] or "(inconnu)", "active_sec": r["active_sec"] or 0}
        for r in report_repository.fetch_project_by_app(project_id)
    ]
    return {
        "project": {
            "id": meta["id"],
            "client": meta["client"] or "",
            "video_name": meta["video_name"],
            "version": meta["version"],
            "estimated_duration_sec": meta["estimated_duration_sec"],
            "assigned_employee_name": meta["employee_name"],
            "spent_sec": spent,
        },
        "daily": daily,
        "by_employee": by_employee,
        "by_app": by_app,
    }


def day_activity(date, employee_id, space_id=None):
    """Segments d'un jour (YYYY-MM-DD) pour la frise par monteur."""
    lo = datetime.fromisoformat(date)
    hi = datetime.fromisoformat(date + "T23:59:59")
    rows = report_repository.fetch_day_segments(lo, hi, employee_id, space_id)
    segments = [{
        "employee_id": r["employee_id"],
        "employee_name": r["employee_name"] or r["employee_id"],
        "project": r["project"],
        "client": r["client"],
        "version": r["version"],
        "state": r["state"],
        "start_ts": _iso(r["start_ts"]),
        "end_ts": _iso(r["end_ts"]),
        "duration_sec": r["duration_sec"] or 0,
    } for r in rows]
    return {"segments": segments}


def calendar(days, date_from, date_to, employee_id, space_id=None):
    lo, hi = _range(days, date_from, date_to)
    rows = report_repository.fetch_calendar(lo, hi, employee_id, space_id)
    events = []
    for r in rows:
        active = r["active_sec"] or 0
        if active <= 0:
            continue  # on n'affiche que le travail reel (actif)
        events.append({
            "day": str(r["day"]),
            "employee_id": r["employee_id"],
            "employee_name": r["employee_name"] or r["employee_id"],
            "client": r["client"],
            "project": r["project"],
            "version": r["version"],
            "active_sec": active,
            "idle_sec": r["idle_sec"] or 0,
        })
    return {"events": events}
