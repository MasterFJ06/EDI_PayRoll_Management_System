import type { Permission, Role } from "@/types";

// Centralized role -> permission matrix. This is a UI/UX convenience only;
// the FastAPI backend must independently enforce authorization via JWT +
// permission checks on every endpoint.
export const ROLE_PERMISSIONS: Record<Role, Permission[]> = {
  Employee: [
    "employee.view.self",
    "attendance.view.self",
    "leave.apply",
    "leave.view.self",
    "salary.view.self",
    "payslip.view.self",
  ],
  Manager: [
    "employee.view.self",
    "employee.view.all",
    "attendance.view.self",
    "attendance.view.all",
    "leave.apply",
    "leave.view.self",
    "leave.view.all",
    "leave.approve",
    "leave.reject",
    "salary.view.self",
    "payslip.view.self",
    "reports.view",
  ],
  HR: [
    "employee.view.all",
    "employee.create",
    "employee.update",
    "employee.delete",
    "org.manage",
    "attendance.view.all",
    "attendance.create",
    "attendance.update",
    "leave.view.all",
    "leave.approve",
    "leave.reject",
    "salary.view.self",
    "payslip.view.self",
    "reports.view",
    "reports.export",
    "audit.view",
  ],
  "Payroll Administrator": [
    "employee.view.all",
    "attendance.view.all",
    "leave.view.all",
    "salary.view.all",
    "salary.create",
    "salary.update",
    "payroll.view",
    "payroll.process",
    "payroll.approve",
    "payroll.validate",
    "payslip.view.all",
    "payslip.generate",
    "reports.view",
    "reports.export",
    "audit.view",
  ],
  "System Administrator": [
    "users.manage",
    "roles.manage",
    "org.manage",
    "employee.view.all",
    "audit.view",
    "backup.create",
    "backup.restore",
    "monitoring.view",
    "reports.view",
  ],
  Management: [
    "employee.view.all",
    "attendance.view.all",
    "leave.view.all",
    "salary.view.all",
    "payroll.view",
    "reports.view",
    "reports.export",
    "audit.view",
  ],
};

export function hasPermission(role: Role | undefined, permission: Permission): boolean {
  if (!role) return false;
  // The System Administrator is the full-access role in the demo.
  if (role === "System Administrator") return true;
  return ROLE_PERMISSIONS[role]?.includes(permission) ?? false;
}

export function hasAnyPermission(role: Role | undefined, permissions: Permission[]): boolean {
  return permissions.some((p) => hasPermission(role, p));
}

export const ALL_ROLES: Role[] = [
  "Employee",
  "Manager",
  "HR",
  "Payroll Administrator",
  "System Administrator",
  "Management",
];

export const ALL_PERMISSIONS: Permission[] = Array.from(
  new Set(Object.values(ROLE_PERMISSIONS).flat())
).sort() as Permission[];
