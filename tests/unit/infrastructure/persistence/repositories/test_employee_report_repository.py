from datetime import date

from sqlalchemy import create_engine, delete, event
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models.department import Department
from app.infrastructure.persistence.models.designation import Designation
from app.infrastructure.persistence.models.employee import Employee
from app.infrastructure.persistence.repositories.employee_repository import EmployeeRepository


def test_report_query_is_bounded_filtered_ordered_and_preserves_missing_labels() -> None:
    engine = create_engine("sqlite://")
    statements: list[str] = []
    event.listen(
        engine,
        "before_cursor_execute",
        lambda connection, cursor, statement, parameters, context, executemany:
            statements.append(statement),
    )
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE TABLE departments (department_id INTEGER PRIMARY KEY, "
                "department_code VARCHAR(30) NOT NULL, department_name VARCHAR(100) NOT NULL, "
                "status VARCHAR(20) NOT NULL, created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, "
                "updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL)"
            )
            connection.exec_driver_sql(
                "CREATE TABLE designations (designation_id INTEGER PRIMARY KEY, "
                "designation_code VARCHAR(30) NOT NULL, designation_name VARCHAR(100) NOT NULL, "
                "status VARCHAR(20) NOT NULL, created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, "
                "updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL)"
            )
            connection.exec_driver_sql(
                "CREATE TABLE employees (employee_id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "employee_code VARCHAR(30) NOT NULL, user_id INTEGER, first_name VARCHAR(100) NOT NULL, "
                "last_name VARCHAR(100) NOT NULL, department_id INTEGER NOT NULL, designation_id INTEGER NOT NULL, "
                "manager_employee_id INTEGER, joining_date DATE NOT NULL, employment_end_date DATE, "
                "employment_status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE', "
                "created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, "
                "updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL)"
            )
        with Session(engine) as session:
            department = Department(
                department_code="D1", department_name="Current Dept", status="ACTIVE"
            )
            designation = Designation(
                designation_code="T1", designation_name="Current Title", status="ACTIVE"
            )
            session.add_all([department, designation])
            session.flush()
            session.add_all([
                Employee(employee_code="EMP-2", first_name="Two", last_name="User",
                         department_id=department.department_id, designation_id=designation.designation_id,
                         joining_date=date(2020, 1, 1), employment_status="ACTIVE", employee_id=20),
                Employee(employee_code="EMP-1", first_name="One", last_name="User",
                         department_id=department.department_id, designation_id=designation.designation_id,
                         joining_date=date(2020, 1, 1), employment_status="TERMINATED", employee_id=10),
            ])
            session.flush()
            repository = EmployeeRepository(session)
            rows = repository.list_report_page(
                employee_code=None,
                department_id=department.department_id,
                designation_id=designation.designation_id,
                employment_status=None,
                after_employee_id=None,
                limit=1,
            )
            assert len(rows) == 1
            assert rows[0].employee_id == 10
            assert rows[0].employee_code == "EMP-1"
            assert rows[0].department_name == "Current Dept"
            assert rows[0].designation_name == "Current Title"
            report_selects = [
                sql for sql in statements if sql.lstrip().upper().startswith("SELECT")
            ]
            assert len(report_selects) == 1
            assert "employees.employee_id" in report_selects[0]
            assert "departments.department_name" in report_selects[0]
            assert "designations.designation_name" in report_selects[0]
            assert "employees.user_id" not in report_selects[0]
            assert "manager_employee_id" not in report_selects[0]
            assert "LIMIT" in report_selects[0].upper()
            assert "LEFT OUTER JOIN departments" in report_selects[0]
            assert "LEFT OUTER JOIN designations" in report_selects[0]
            assert "employees.department_id =" in report_selects[0]
            assert "employees.designation_id =" in report_selects[0]

            next_rows = repository.list_report_page(
                employee_code=None, department_id=None, designation_id=None,
                employment_status=None, after_employee_id=10, limit=2,
            )
            assert [row.employee_id for row in next_rows] == [20]
            report_selects = [
                sql for sql in statements if sql.lstrip().upper().startswith("SELECT")
            ]
            assert len(report_selects) == 2
            assert "employees.employee_id >" in report_selects[1]
            assert "LIMIT" in report_selects[1].upper()

            session.execute(delete(Department))
            session.execute(delete(Designation))
            missing_labels = repository.list_report_page(
                employee_code="EMP-2", department_id=None, designation_id=None,
                employment_status="ACTIVE", after_employee_id=None, limit=2,
            )
            assert len(missing_labels) == 1
            assert missing_labels[0].department_name is None
            assert missing_labels[0].designation_name is None
    finally:
        engine.dispose()
