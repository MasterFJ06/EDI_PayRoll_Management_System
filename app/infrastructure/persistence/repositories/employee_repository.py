from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.employee.employee_report import EmployeeReportRecord
from app.infrastructure.persistence.models.department import Department
from app.infrastructure.persistence.models.designation import Designation
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

    def list_report_page(
        self,
        employee_code: str | None,
        department_id: int | None,
        designation_id: int | None,
        employment_status: str | None,
        after_employee_id: int | None,
        limit: int,
    ) -> list[EmployeeReportRecord]:
        statement = (
            select(
                Employee.employee_id,
                Employee.employee_code,
                Employee.first_name,
                Employee.last_name,
                Employee.department_id,
                Department.department_name,
                Employee.designation_id,
                Designation.designation_name,
                Employee.joining_date,
                Employee.employment_end_date,
                Employee.employment_status,
            )
            .select_from(Employee)
            .outerjoin(Department, Department.department_id == Employee.department_id)
            .outerjoin(Designation, Designation.designation_id == Employee.designation_id)
        )
        if employee_code is not None:
            statement = statement.where(Employee.employee_code == employee_code)
        if department_id is not None:
            statement = statement.where(Employee.department_id == department_id)
        if designation_id is not None:
            statement = statement.where(Employee.designation_id == designation_id)
        if employment_status is not None:
            statement = statement.where(Employee.employment_status == employment_status)
        if after_employee_id is not None:
            statement = statement.where(Employee.employee_id > after_employee_id)
        statement = statement.order_by(Employee.employee_id.asc()).limit(limit)

        return [
            EmployeeReportRecord(
                employee_id=row.employee_id,
                employee_code=row.employee_code,
                first_name=row.first_name,
                last_name=row.last_name,
                department_id=row.department_id,
                department_name=row.department_name,
                designation_id=row.designation_id,
                designation_name=row.designation_name,
                joining_date=row.joining_date,
                employment_end_date=row.employment_end_date,
                employment_status=row.employment_status,
            )
            for row in self.session.execute(statement)
        ]

    def add(self, employee: Employee) -> Employee:
        self.session.add(employee)
        self.session.flush()
        return employee
