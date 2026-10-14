from pathlib import Path


def test_employee_report_seed_assigns_only_employee_read_to_hr_role() -> None:
    seed = Path("database/seed.sql").read_text(encoding="utf-8")
    assert "VALUES ('HR Administrator', 'Administration of employee reporting.')" in seed
    assert "('report.employee.read', 'View organization-wide employee reports.')" in seed
    assert "p.permission_code = 'report.employee.read'" in seed
    assert "WHERE r.role_name = 'HR Administrator'" in seed

    role_assignments = seed.split("INSERT IGNORE INTO role_permissions")[1:]
    (
        payroll_assignment,
        employee_report_assignment,
        attendance_assignment,
        leave_assignment,
        leave_write_assignment,
    ) = role_assignments
    assert "report.employee.read" not in payroll_assignment
    assert "p.permission_code = 'report.employee.read'" in employee_report_assignment
    assert "p.permission_code = 'report.attendance.read'" in attendance_assignment
    for hr_assignment in (employee_report_assignment, attendance_assignment, leave_assignment):
        assert "payroll." not in hr_assignment
        assert "report.payroll.read" not in hr_assignment
    assert "report.leave.read" not in payroll_assignment
    assert "p.permission_code = 'report.leave.read'" in leave_assignment
    assert "workforce.leave.request.create_for_others" not in leave_assignment
    assert "workforce.leave.balance.manage_for_others" not in leave_assignment
    assert "workforce.leave.request.create_for_others" in leave_write_assignment
    assert "workforce.leave.balance.manage_for_others" in leave_write_assignment
    assert "WHERE r.role_name = 'HR Administrator'" in leave_write_assignment
