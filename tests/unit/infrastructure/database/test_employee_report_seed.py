from pathlib import Path


def test_employee_report_seed_assigns_only_employee_read_to_hr_role() -> None:
    seed = Path("database/seed.sql").read_text(encoding="utf-8")
    assert "VALUES ('HR Administrator', 'Administration of employee reporting.')" in seed
    assert "('report.employee.read', 'View organization-wide employee reports.')" in seed
    assert "p.permission_code = 'report.employee.read'" in seed
    assert "WHERE r.role_name = 'HR Administrator'" in seed

    role_assignments = seed.split("INSERT IGNORE INTO role_permissions")[1:]
    payroll_assignment, hr_assignment = role_assignments
    assert "report.employee.read" not in payroll_assignment
    assert "p.permission_code = 'report.employee.read'" in hr_assignment
    assert "payroll." not in hr_assignment
    assert "report.payroll.read" not in hr_assignment
    assert "report.attendance.read" not in hr_assignment
    assert "report.leave.read" not in hr_assignment
