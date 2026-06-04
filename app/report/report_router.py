from fastapi import APIRouter, Depends

from app.report import report_service
from app.security.security import check_dashboard

router = APIRouter()


@router.get("/api/summary")
def summary(
    _=Depends(check_dashboard),
    days: int = 7,
    date_from: str | None = None,
    date_to: str | None = None,
):
    return report_service.summary(days, date_from, date_to)


@router.get("/api/projects")
def projects(
    _=Depends(check_dashboard),
    days: int = 7,
    date_from: str | None = None,
    date_to: str | None = None,
    employee_id: str | None = None,
):
    return report_service.projects(days, date_from, date_to, employee_id)


@router.get("/api/apps")
def apps(
    _=Depends(check_dashboard),
    days: int = 7,
    date_from: str | None = None,
    date_to: str | None = None,
    employee_id: str | None = None,
):
    return report_service.apps(days, date_from, date_to, employee_id)


@router.get("/api/details")
def details(
    _=Depends(check_dashboard),
    days: int = 7,
    date_from: str | None = None,
    date_to: str | None = None,
    employee_id: str | None = None,
):
    return report_service.details(days, date_from, date_to, employee_id)


@router.get("/api/timeline")
def timeline(
    employee_id: str,
    _=Depends(check_dashboard),
    date_from: str | None = None,
    date_to: str | None = None,
    days: int = 1,
):
    return report_service.timeline(employee_id, days, date_from, date_to)
