from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.infrastructure.persistence.repositories.employee_salary_assignment_repository import (
    EmployeeSalaryAssignmentRepository,
)


def test_applicable_assignment_repository_returns_all_inclusive_matches():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE employee_salary_assignments ("
            "salary_assignment_id INTEGER PRIMARY KEY, employee_id INTEGER NOT NULL, "
            "salary_revision_id INTEGER NOT NULL, effective_from DATE NOT NULL, "
            "effective_to DATE NULL, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)"
        )
        connection.exec_driver_sql(
            "INSERT INTO employee_salary_assignments "
            "(salary_assignment_id, employee_id, salary_revision_id, effective_from, effective_to) "
            "VALUES (1, 7, 20, '2026-01-01', '2026-01-10'), "
            "(2, 7, 21, '2026-01-10', NULL), "
            "(3, 7, 22, '2026-01-11', NULL), "
            "(4, 8, 23, '2026-01-01', NULL)"
        )

    with Session(engine) as session:
        repository = EmployeeSalaryAssignmentRepository(session)
        matches = repository.get_applicable_for_employee(7, date(2026, 1, 10))
        period_matches = repository.get_intersecting_for_employee(
            7, date(2026, 1, 10), date(2026, 1, 10)
        )

    assert [item.salary_assignment_id for item in matches] == [1, 2]
    assert [item.salary_assignment_id for item in period_matches] == [1, 2]
    engine.dispose()
