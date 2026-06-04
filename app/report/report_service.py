from datetime import datetime, timezone, timedelta

from app.report import report_repository


def _range(days, date_from, date_to):
    if date_from and date_to:
        return date_from, date_to + "T23:59:59"
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    return start.isoformat(), end.isoformat()


def summary(days, date_from, date_to):
    lo, hi = _range(days, date_from, date_to)
    rows = report_repository.fetch_summary_totals(lo, hi)
    current = {c["employee_id"]: c for c in report_repository.fetch_current_activity()}

    result = []
    for r in rows:
        active = r["active_sec"] or 0
        idle = r["idle_sec"] or 0
        paused = r["paused_sec"] or 0
        # La pause n'est ni active ni inactive : exclue du taux d'activite.
        total = active + idle
        cur = current.get(r["employee_id"])
        result.append({
            "employee_id": r["employee_id"],
            "employee_name": r["employee_name"] or r["employee_id"],
            "active_sec": active,
            "idle_sec": idle,
            "paused_sec": paused,
            "activity_rate": round(100 * active / total, 1) if total else 0,
            "last_seen": r["last_seen"],
            "current_app": cur["app"] if cur else None,
            "current_title": cur["window_title"] if cur else None,
            "current_project": cur["project"] if cur else None,
            "current_state": cur["state"] if cur else None,
        })
    return {"range": {"from": lo, "to": hi}, "employees": result}


def projects(days, date_from, date_to, employee_id):
    lo, hi = _range(days, date_from, date_to)
    rows = report_repository.fetch_projects(lo, hi, employee_id)
    return {"projects": [dict(r) for r in rows]}


def apps(days, date_from, date_to, employee_id):
    lo, hi = _range(days, date_from, date_to)
    rows = report_repository.fetch_apps(lo, hi, employee_id)
    return {"apps": [dict(r) for r in rows]}


def details(days, date_from, date_to, employee_id):
    lo, hi = _range(days, date_from, date_to)
    rows = report_repository.fetch_details(lo, hi, employee_id)
    return {"details": [dict(r) for r in rows]}


def timeline(employee_id, days, date_from, date_to):
    lo, hi = _range(days, date_from, date_to)
    rows = report_repository.fetch_timeline(employee_id, lo, hi)
    return {"segments": [dict(r) for r in rows]}
