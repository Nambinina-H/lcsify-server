from app.projects import project_repository
from app.projects.schemas import ProjectIn, RegisterIn


def list_projects():
    return project_repository.list_all()


def create_project(payload: ProjectIn):
    return project_repository.create(payload.model_dump())


def update_project(project_id, payload: ProjectIn):
    return project_repository.update(project_id, payload.model_dump())


def delete_project(project_id):
    return project_repository.delete(project_id)


def list_for_employee(employee_id):
    return project_repository.list_for_employee(employee_id)


def list_employees():
    return project_repository.list_employees()


def register_employee(payload: RegisterIn):
    return project_repository.register_employee(
        payload.employee_id, payload.employee_name
    )
