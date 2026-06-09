from fastapi import APIRouter, Depends, HTTPException

from app.report import report_service
from app.security.security import get_current_user

router = APIRouter()


@router.get("/api/summary")
def summary(
    _=Depends(get_current_user),
    days: int = 7,
    date_from: str | None = None,
    date_to: str | None = None,
):
    return report_service.summary(days, date_from, date_to)


@router.get("/api/projects")
def projects(
    _=Depends(get_current_user),
    days: int = 7,
    date_from: str | None = None,
    date_to: str | None = None,
    employee_id: str | None = None,
):
    return report_service.projects(days, date_from, date_to, employee_id)


@router.get("/api/apps")
def apps(
    _=Depends(get_current_user),
    days: int = 7,
    date_from: str | None = None,
    date_to: str | None = None,
    employee_id: str | None = None,
):
    return report_service.apps(days, date_from, date_to, employee_id)


@router.get("/api/details")
def details(
    _=Depends(get_current_user),
    days: int = 7,
    date_from: str | None = None,
    date_to: str | None = None,
    employee_id: str | None = None,
):
    return report_service.details(days, date_from, date_to, employee_id)


@router.get("/api/timeline")
def timeline(
    employee_id: str,
    _=Depends(get_current_user),
    date_from: str | None = None,
    date_to: str | None = None,
    days: int = 1,
):
    return report_service.timeline(employee_id, days, date_from, date_to)


@router.get("/api/calendar")
def calendar(
    _=Depends(get_current_user),
    days: int = 30,
    date_from: str | None = None,
    date_to: str | None = None,
    employee_id: str | None = None,
):
    return report_service.calendar(days, date_from, date_to, employee_id)


@router.get("/api/day-activity")
def day_activity(
    date: str,
    _=Depends(get_current_user),
    employee_id: str | None = None,
):
    return report_service.day_activity(date, employee_id)


@router.get("/api/project-report")
def project_report(project_id: int, _=Depends(get_current_user)):
    result = report_service.project_report(project_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Projet introuvable")
    return result
