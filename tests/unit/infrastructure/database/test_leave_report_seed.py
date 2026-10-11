from pathlib import Path


def test_leave_report_permission_is_assigned_only_to_hr_administrator() -> None:
    seed = Path("database/seed.sql").read_text(encoding="utf-8")
    assert "('report.leave.read', 'View organization-wide Leave reports.')" in seed

    assignments = seed.split("INSERT IGNORE INTO role_permissions")[1:]
    payroll, employee_report, attendance_report, leave_report = assignments
    assert "report.leave.read" not in payroll
    assert "report.leave.read" not in employee_report
    assert "report.leave.read" not in attendance_report
    assert "p.permission_code = 'report.leave.read'" in leave_report
    assert "WHERE r.role_name = 'HR Administrator'" in leave_report
    assert "payroll." not in leave_report
    assert "report.payroll.read" not in leave_report
    assert "report.employee.read" not in leave_report
    assert "report.attendance.read" not in leave_report
