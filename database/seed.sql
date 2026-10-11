-- Idempotent RBAC catalog seed. This does not assign any user to a role.
INSERT IGNORE INTO roles (role_name, description)
VALUES ('Payroll Administrator', 'Administration of payroll operations.');

INSERT IGNORE INTO roles (role_name, description)
VALUES ('HR Administrator', 'Administration of employee reporting.');

INSERT IGNORE INTO permissions (permission_code, description)
VALUES
    ('payroll.run.create', 'Create a payroll run.'),
    ('payroll.run.read', 'View payroll runs.'),
    ('payroll.run.process', 'Process a payroll run.'),
    ('payroll.run.recover', 'Recover an expired payroll processing attempt.'),
    ('payroll.run.retry', 'Retry a failed payroll run.'),
    ('payroll.run.finalize', 'Finalize a processed payroll run.'),
    ('payroll.payslip.create', 'Generate an individual payslip record.'),
    ('report.payroll.read', 'View finalized payroll run summaries, results, and component details.'),
    ('report.employee.read', 'View organization-wide employee reports.'),
    ('report.attendance.read', 'View organization-wide attendance reports.'),
    ('report.leave.read', 'View organization-wide Leave reports.'),
    ('organization.calendar.read', 'View organization work calendar versions.'),
    ('organization.calendar.manage', 'Manage organization work calendar versions and overrides.'),
    ('workforce.leave_type.manage', 'Create and manage Leave Types.'),
    ('workforce.leave.approve', 'Approve Leave Requests.'),
    ('workforce.leave.reject', 'Reject Leave Requests.'),
    ('workforce.leave.cancel', 'Cancel Leave Requests.'),
    ('workforce.overtime_policy.read', 'View Workforce overtime policy versions.'),
    ('workforce.overtime_policy.manage', 'Manage Workforce overtime policy versions.');

INSERT IGNORE INTO role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM roles AS r
JOIN permissions AS p
  ON p.permission_code IN (
      'payroll.run.create',
      'payroll.run.read',
      'payroll.run.process',
      'payroll.run.recover',
      'payroll.run.retry',
      'payroll.run.finalize',
      'payroll.payslip.create',
      'report.payroll.read'
  )
WHERE r.role_name = 'Payroll Administrator';

INSERT IGNORE INTO role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM roles AS r
JOIN permissions AS p
  ON p.permission_code = 'report.employee.read'
WHERE r.role_name = 'HR Administrator';

INSERT IGNORE INTO role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM roles AS r
JOIN permissions AS p
  ON p.permission_code = 'report.attendance.read'
WHERE r.role_name = 'HR Administrator';

INSERT IGNORE INTO role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM roles AS r
JOIN permissions AS p
  ON p.permission_code = 'report.leave.read'
WHERE r.role_name = 'HR Administrator';
