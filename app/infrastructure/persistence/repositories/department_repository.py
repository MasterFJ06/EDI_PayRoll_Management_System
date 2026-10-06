from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.organization.repository import DepartmentRepository as DepartmentRepositoryContract
from app.infrastructure.persistence.models.department import Department


class SQLAlchemyDepartmentRepository(DepartmentRepositoryContract):
    """Repository for department persistence operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, department_id: int) -> Department | None:
        statement = select(Department).where(
            Department.department_id == department_id
        )
        return self.session.scalar(statement)

    def get_by_code(self, department_code: str) -> Department | None:
        statement = select(Department).where(
            Department.department_code == department_code
        )
        return self.session.scalar(statement)

    def get_by_name(self, department_name: str) -> Department | None:
        statement = select(Department).where(
            Department.department_name == department_name
        )
        return self.session.scalar(statement)

    def get_all(self) -> list[Department]:
        statement = select(Department).order_by(Department.department_id.asc())
        return list(self.session.scalars(statement).all())

    def add(self, department: Department) -> Department:
        self.session.add(department)
        self.session.flush()
        return department

    def update(self, department: Department) -> Department:
        self.session.merge(department)
        self.session.flush()
        return department

    def delete(self, department_id: int) -> None:
        dept = self.get_by_id(department_id)
        if dept is not None:
            dept.status = "INACTIVE"
            self.session.flush()