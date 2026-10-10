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

    def get_by_id_for_update(self, employee_id: int) -> Employee | None:
        statement = (
            select(Employee)
            .where(Employee.employee_id == employee_id)
            .with_for_update()
        )
        return self.session.scalar(statement)

    def list_all(self) -> list[Employee]:
        statement = select(Employee).order_by(Employee.employee_id)
        return list(self.session.scalars(statement).all())

    def add(self, employee: Employee) -> Employee:
        self.session.add(employee)
        self.session.flush()
        return employee
