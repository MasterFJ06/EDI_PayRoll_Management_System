from datetime import date

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.infrastructure.persistence.repositories.attendance_repository import (
    AttendanceRepository,
)


def test_report_query_projects_filters_inclusive_dates_and_keyset_paginates() -> None:
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
                "CREATE TABLE departments (department_id INTEGER PRIMARY KEY, department_name TEXT)"
            )
            connection.exec_driver_sql(
                "CREATE TABLE designations (designation_id INTEGER PRIMARY KEY, designation_name TEXT)"
            )
            connection.exec_driver_sql(
                "CREATE TABLE employees (employee_id INTEGER PRIMARY KEY, employee_code TEXT, "
                "first_name TEXT, last_name TEXT, department_id INTEGER, designation_id INTEGER)"
            )
            connection.exec_driver_sql(
                "CREATE TABLE attendance_records (attendance_id INTEGER PRIMARY KEY, employee_id INTEGER, "
                "attendance_date DATE, attendance_status TEXT, check_in_time DATETIME, check_out_time DATETIME)"
            )
            connection.exec_driver_sql(
                "INSERT INTO departments VALUES (4, 'Finance'), (5, 'Operations')"
            )
            connection.exec_driver_sql(
                "INSERT INTO designations VALUES (8, 'Analyst'), (9, 'Clerk')"
            )
            connection.exec_driver_sql(
                "INSERT INTO employees VALUES "
                "(10, 'E10', 'Asha', 'Patel', 4, 8), "
                "(11, 'E11', 'Ben', 'Lee', 4, 8), "
                "(12, 'E12', 'Cara', 'Wu', 5, 9)"
            )
            connection.exec_driver_sql(
                "INSERT INTO attendance_records VALUES "
                "(21, 10, '2026-01-10', 'PRESENT', NULL, NULL), "
                "(23, 11, '2026-01-10', 'ABSENT', NULL, NULL), "
                "(25, 12, '2026-01-11', 'HOLIDAY', NULL, NULL)"
            )

        with Session(engine) as session:
            repository = AttendanceRepository(session)
            first = repository.list_report_page(
                date_from=date(2026, 1, 10),
                date_to=date(2026, 1, 10),
                employee_id=None,
                department_id=4,
                attendance_status=None,
                after_attendance_date=None,
                after_attendance_id=None,
                limit=1,
            )
            assert len(first) == 1
            assert first[0].attendance_id == 21
            assert first[0].attendance_date == date(2026, 1, 10)
            assert first[0].department_name == "Finance"
            assert first[0].designation_name == "Analyst"
            assert first[0].check_in_time is None
            assert first[0].check_out_time is None

            second = repository.list_report_page(
                date_from=date(2026, 1, 10),
                date_to=date(2026, 1, 10),
                employee_id=None,
                department_id=4,
                attendance_status=None,
                after_attendance_date=date(2026, 1, 10),
                after_attendance_id=21,
                limit=2,
            )
            assert [record.attendance_id for record in second] == [23]

            filtered = repository.list_report_page(
                date_from=date(2026, 1, 10),
                date_to=date(2026, 1, 11),
                employee_id=12,
                department_id=5,
                attendance_status="HOLIDAY",
                after_attendance_date=None,
                after_attendance_id=None,
                limit=2,
            )
            assert [record.attendance_id for record in filtered] == [25]
            assert repository.list_report_page(
                date_from=None,
                date_to=None,
                employee_id=999,
                department_id=None,
                attendance_status=None,
                after_attendance_date=None,
                after_attendance_id=None,
                limit=2,
            ) == []

            selects = [statement for statement in statements if statement.lstrip().upper().startswith("SELECT")]
            assert len(selects) == 4
            report_sql = selects[0]
            for selected_column in (
                "attendance_records.attendance_id",
                "employees.employee_code",
                "employees.first_name",
                "employees.last_name",
                "departments.department_name",
                "designations.designation_name",
                "attendance_records.check_in_time",
                "attendance_records.check_out_time",
            ):
                assert selected_column in report_sql
            assert "attendance_records.user_id" not in report_sql
            assert "LEFT OUTER JOIN departments" in report_sql
            assert "LEFT OUTER JOIN designations" in report_sql
            assert "attendance_records.attendance_date >=" in report_sql
            assert "attendance_records.attendance_date <=" in report_sql
            assert "ORDER BY attendance_records.attendance_date ASC, attendance_records.attendance_id ASC" in report_sql
            assert "LIMIT" in report_sql.upper()
    finally:
        engine.dispose()
