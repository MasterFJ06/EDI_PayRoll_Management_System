from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models.employee import Employee


class EmployeeRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, employee_id: int) -> Employee | None:
        statement = select(Employee).where(
            Employee.employee_id == employee_id
        )
        return self.session.scalar(statement)

    def get_by_code(self, employee_code: str) -> Employee | None:
        statement = select(Employee).where(
            Employee.employee_code == employee_code
        )
        return self.session.scalar(statement)

    def get_by_user_id(self, user_id: int) -> Employee | None:
        statement = select(Employee).where(
            Employee.user_id == user_id
        )
        return self.session.scalar(statement)

    def add(self, employee: Employee) -> Employee:
        self.session.add(employee)
        self.session.flush()
        return employee