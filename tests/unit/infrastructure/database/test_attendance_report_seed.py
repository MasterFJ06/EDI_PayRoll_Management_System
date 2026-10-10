from pathlib import Path


def test_attendance_report_permission_is_assigned_only_to_hr_administrator() -> None:
    seed = Path("database/seed.sql").read_text(encoding="utf-8")
    assert "('report.attendance.read', 'View organization-wide attendance reports.')" in seed

    assignments = seed.split("INSERT IGNORE INTO role_permissions")[1:]
    payroll_assignment, employee_report_assignment, attendance_assignment = assignments

    assert "report.attendance.read" not in payroll_assignment
    assert "p.permission_code = 'report.employee.read'" in employee_report_assignment
    assert "p.permission_code = 'report.attendance.read'" in attendance_assignment
    assert "WHERE r.role_name = 'HR Administrator'" in attendance_assignment
    assert "payroll." not in attendance_assignment
    assert "report.payroll.read" not in attendance_assignment
    assert "report.employee.read" not in attendance_assignment
