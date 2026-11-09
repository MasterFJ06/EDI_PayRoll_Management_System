"""Application service for RBAC initialization, role assignment, and permission checking."""
from typing import Any
from app.application.common.unit_of_work import UnitOfWork
from app.domain.shared.exceptions import BusinessRuleViolation
from app.infrastructure.persistence.models.role import Permission, Role, RolePermission, UserRole

# Standard roles with descriptions
STANDARD_ROLES: list[dict[str, str]] = [
    {
        "name": "System Administrator",
        "description": "Full administrative access, user management, and system configuration.",
    },
    {
        "name": "HR",
        "description": "Employee lifecycle, organization structure, attendance and leave administration.",
    },
    {
        "name": "Payroll Administrator",
        "description": "Salary structures, compensation, payroll processing, validation, and payslips.",
    },
    {
        "name": "Manager",
        "description": "Team visibility, attendance tracking, and leave approvals for direct reports.",
    },
    {
        "name": "Employee",
        "description": "Self-service access to personal profile, attendance, leave requests, and payslips.",
    },
    {
        "name": "Management",
        "description": "Executive read-only visibility into workforce, payroll, and organizational reporting.",
    },
]

# Standard permission definitions (code and description)
STANDARD_PERMISSIONS: list[tuple[str, str]] = [
    # Employee
    ("employee.view.self", "View own employee profile"),
    ("employee.view.all", "View all employee records across the organization"),
    ("employee.create", "Create new employee records"),
    ("employee.update", "Update existing employee records"),
    ("employee.delete", "Deactivate or remove employee records"),
    # Attendance
    ("attendance.view.self", "View own attendance records"),
    ("attendance.view.all", "View attendance records for all employees"),
    ("attendance.create", "Mark or log employee attendance"),
    ("attendance.update", "Correct or adjust attendance entries"),
    # Leave
    ("leave.apply", "Apply for leave requests"),
    ("leave.view.self", "View own leave requests and balances"),
    ("leave.view.all", "View leave requests across the organization"),
    ("leave.approve", "Approve pending leave requests"),
    ("leave.reject", "Reject pending leave requests"),
    # Salary
    ("salary.view.self", "View own salary structure and compensation"),
    ("salary.view.all", "View salary structures across the organization"),
    ("salary.create", "Create new salary structures and revisions"),
    ("salary.update", "Update existing salary structures and assignments"),
    # Payroll
    ("payroll.view", "View payroll processing dashboard and records"),
    ("payroll.process", "Run monthly payroll calculation batches"),
    ("payroll.approve", "Approve calculated payroll batches for disbursement"),
    ("payroll.validate", "Validate payroll records and view reconciliation issues"),
    # Payslip
    ("payslip.view.self", "View and download own payslips"),
    ("payslip.view.all", "View all employee payslips across the organization"),
    ("payslip.generate", "Generate monthly payslips and PDF exports"),
    # Reports
    ("reports.view", "View analytics and reports"),
    ("reports.export", "Export organizational data and reports"),
    # Audit
    ("audit.view", "View system security audit logs"),
    # Infrastructure
    ("backup.create", "Create system database backups"),
    ("backup.restore", "Restore system database from backups"),
    ("monitoring.view", "View server health and operational telemetry"),
    # Administration
    ("users.manage", "Create, view, update, and deactivate user accounts"),
    ("roles.manage", "Assign and modify user roles and permissions"),
    ("org.manage", "Manage departments and designations"),
]

# Role to permission mapping matching frontend config/permissions.ts
ROLE_PERMISSIONS_MAP: dict[str, list[str]] = {
    "Employee": [
        "employee.view.self",
        "attendance.view.self",
        "leave.apply",
        "leave.view.self",
        "salary.view.self",
        "payslip.view.self",
    ],
    "Manager": [
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
    "HR": [
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
        code for code, _ in STANDARD_PERMISSIONS
    ],
    "Management": [
        "employee.view.all",
        "attendance.view.all",
        "leave.view.all",
        "salary.view.all",
        "payroll.view",
        "reports.view",
        "reports.export",
        "audit.view",
    ],
}

# Role aliases for normalization
ROLE_ALIASES: dict[str, str] = {
    "admin": "System Administrator",
    "administrator": "System Administrator",
    "system administrator": "System Administrator",
    "member": "Employee",
    "employee": "Employee",
    "hr": "HR",
    "payroll": "Payroll Administrator",
    "payroll administrator": "Payroll Administrator",
    "manager": "Manager",
    "management": "Management",
}


def normalize_role_name(role_name: str) -> str:
    """Normalize role aliases to the canonical role name."""
    cleaned = role_name.strip()
    return ROLE_ALIASES.get(cleaned.lower(), cleaned)


class RBACService:
    """Service orchestrating RBAC initialization, role assignments, and permission checks."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def init_rbac(self) -> dict[str, int]:
        """Idempotently initialize all standard permissions, roles, and mappings."""
        if getattr(self.uow, "roles", None) is None:
            raise RuntimeError("Role repository not available on Unit of Work.")

        created_perms = 0
        created_roles = 0
        created_mappings = 0

        # 1. Initialize permissions
        perm_map: dict[str, Permission] = {}
        for code, desc in STANDARD_PERMISSIONS:
            existing = self.uow.roles.get_permission_by_code(code)
            if existing is None:
                new_perm = Permission(permission_code=code, description=desc)
                existing = self.uow.roles.add_permission(new_perm)
                created_perms += 1
            perm_map[code] = existing

        # 2. Initialize roles
        role_map: dict[str, Role] = {}
        for role_data in STANDARD_ROLES:
            name = role_data["name"]
            existing = self.uow.roles.get_by_name(name)
            if existing is None:
                new_role = Role(
                    role_name=name,
                    description=role_data["description"],
                    is_active=True,
                )
                existing = self.uow.roles.add(new_role)
                created_roles += 1
            role_map[name] = existing

        # 3. Initialize role-permission mappings
        for role_name, perm_codes in ROLE_PERMISSIONS_MAP.items():
            role = role_map.get(role_name)
            if not role:
                continue
            for p_code in perm_codes:
                perm = perm_map.get(p_code)
                if not perm:
                    continue
                existing_mapping = self.uow.roles.get_role_permission(role.role_id, perm.permission_id)
                if existing_mapping is None:
                    self.uow.roles.add_role_permission(role.role_id, perm.permission_id)
                    created_mappings += 1

        self.uow.commit()

        return {
            "permissions_created": created_perms,
            "roles_created": created_roles,
            "mappings_created": created_mappings,
            "total_permissions": len(perm_map),
            "total_roles": len(role_map),
        }

    def assign_user_role(
        self,
        user_id: int,
        role_name: str,
        assigned_by_user_id: int,
        commit: bool = True,
    ) -> UserRole:
        """Assign a canonical role to a user, replacing any previous role assignments."""
        if getattr(self.uow, "roles", None) is None:
            raise RuntimeError("Role repository not available on Unit of Work.")

        canonical_role = normalize_role_name(role_name)
        role = self.uow.roles.get_by_name(canonical_role)
        if role is None:
            raise BusinessRuleViolation(f"Role '{role_name}' is not recognized.")

        self.uow.roles.remove_user_roles(user_id)
        user_role = self.uow.roles.assign_role(
            user_id=user_id,
            role_id=role.role_id,
            assigned_by_user_id=assigned_by_user_id,
        )
        if commit:
            self.uow.commit()
        return user_role

    def get_user_role_name(self, user_id: int) -> str:
        """Get the primary role name for a user (defaults to 'Employee')."""
        if getattr(self.uow, "roles", None) is None:
            return "Employee"
        roles = self.uow.roles.get_user_roles(user_id)
        if roles:
            return roles[0].role_name
        return "Employee"

    def get_user_permission_codes(self, user_id: int) -> list[str]:
        """Get all permission codes granted to a user across their assigned roles."""
        if getattr(self.uow, "roles", None) is None:
            return ROLE_PERMISSIONS_MAP.get("Employee", [])

        user_roles = self.uow.roles.get_user_roles(user_id)
        if not user_roles:
            return ROLE_PERMISSIONS_MAP.get("Employee", [])

        # If user has System Administrator role, return all permissions
        for r in user_roles:
            if r.role_name == "System Administrator":
                return [code for code, _ in STANDARD_PERMISSIONS]

        perms = self.uow.roles.get_user_permissions(user_id)
        if perms:
            return [p.permission_code for p in perms]

        # Fallback to map if table hasn't mapped yet
        codes: set[str] = set()
        for r in user_roles:
            codes.update(ROLE_PERMISSIONS_MAP.get(r.role_name, []))
        return sorted(codes)

    def user_has_permission(self, user_id: int, permission_code: str) -> bool:
        """Check if a user has a specific permission."""
        perms = self.get_user_permission_codes(user_id)
        return permission_code in perms
