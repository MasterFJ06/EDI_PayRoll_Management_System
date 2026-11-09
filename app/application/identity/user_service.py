from app.api.dependencies import current_user
from app.application.common.unit_of_work import UnitOfWork
from app.application.identity.schemas import (
    UserCreateRequest,
    UserLoginRequest,
    UserMeResponse,
    UserRegistrationRequest,
    UserRegistrationResponse,
    UserResponse,
    UserUpdateRequest,
)
from app.domain.shared.exceptions import BusinessRuleViolation
from app.infrastructure.persistence.models.user import User
from app.infrastructure.security.password import (
    hash_password,
    verify_password,
)


class UserService:
    """Application service for user identity operations."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def register(
        self,
        request: UserRegistrationRequest,
    ) -> UserRegistrationResponse:
        """Register a new system user with the default Employee/Member role."""
        if self.uow.users is None:
            raise RuntimeError("Unit of Work has not been started.")

        existing_username = self.uow.users.get_by_username(request.username)
        if existing_username is not None:
            raise BusinessRuleViolation("Username is already registered.")

        existing_email = self.uow.users.get_by_email(str(request.email))
        if existing_email is not None:
            raise BusinessRuleViolation("Email is already registered.")

        user = User(
            username=request.username,
            email=str(request.email),
            password_hash=hash_password(request.password),
            status="ACTIVE",
        )

        self.uow.users.add(user)

        # Assign default "Employee" role in user_roles table if role repo exists
        if getattr(self.uow, "roles", None) is not None:
            try:
                from app.application.identity.rbac_service import RBACService
                rbac = RBACService(self.uow)
                user_id_val = getattr(user, "user_id", None)
                if user_id_val:
                    rbac.assign_user_role(user_id_val, "Employee", assigned_by_user_id=user_id_val, commit=False)
            except Exception:
                pass

        self.uow.commit()

        return UserRegistrationResponse(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            status=user.status,
        )

    def authenticate(
        self,
        request: UserLoginRequest,
    ) -> User:
        """Authenticate a user using username and password."""
        if self.uow.users is None:
            raise RuntimeError("Unit of Work has not been started.")

        user = self.uow.users.get_by_username(request.username)
        if user is None:
            raise BusinessRuleViolation("Invalid username or password.")

        if not verify_password(request.password, user.password_hash):
            raise BusinessRuleViolation("Invalid username or password.")

        if user.status != "ACTIVE":
            raise BusinessRuleViolation("User account is not active.")

        return user

    def to_user_me(self, user: User) -> UserMeResponse:
        """Convert a User entity to a rich frontend AppUser shape with permissions."""
        # Find linked employee if any
        emp = None
        if getattr(self.uow, "employees", None) is not None:
            emp = self.uow.employees.get_by_user_id(user.user_id)

        first_name = emp.first_name if emp else (user.username.split(".")[0].capitalize() if "." in user.username else user.username.capitalize())
        last_name = emp.last_name if emp else (user.username.split(".")[1].capitalize() if "." in user.username else "")
        emp_code = emp.employee_code if emp else None

        # Determine role and permissions via RBACService
        role_name = "Employee"
        permissions: list[str] = []
        if getattr(self.uow, "roles", None) is not None:
            from app.application.identity.rbac_service import RBACService
            rbac = RBACService(self.uow)
            role_name = rbac.get_user_role_name(user.user_id)
            permissions = rbac.get_user_permission_codes(user.user_id)

        # Fallback role inference for common demo accounts if role is default Employee
        if role_name == "Employee":
            if user.username in {"sysadmin", "admin"}:
                role_name = "System Administrator"
                from app.application.identity.rbac_service import STANDARD_PERMISSIONS
                permissions = [code for code, _ in STANDARD_PERMISSIONS]
            elif user.username in {"payroll.admin"}:
                role_name = "Payroll Administrator"
            elif user.username in {"priya.sharma"}:
                role_name = "HR"
            elif user.username in {"amit.kulkarni"}:
                role_name = "Manager"
            elif user.username in {"management"}:
                role_name = "Management"

        status_str = "Active" if user.status == "ACTIVE" else "Inactive"

        avatar_colors = {
            "Employee": "bg-blue-500",
            "Manager": "bg-indigo-500",
            "HR": "bg-emerald-500",
            "Payroll Administrator": "bg-amber-500",
            "System Administrator": "bg-slate-600",
            "Management": "bg-sky-600",
        }

        return UserMeResponse(
            id=str(user.user_id),
            username=user.username,
            firstName=first_name,
            lastName=last_name,
            email=user.email,
            phone="",
            employeeId=emp_code,
            role=role_name,
            permissions=permissions,
            status=status_str,
            avatarColor=avatar_colors.get(role_name, "bg-blue-500"),
        )

    def list_users(self) -> list[UserResponse]:
        """List all system users."""
        if self.uow.users is None:
            raise RuntimeError("Unit of Work has not been started.")

        users = self.uow.users.get_all()
        result: list[UserResponse] = []
        for u in users:
            me = self.to_user_me(u)
            result.append(
                UserResponse(
                    id=me.id,
                    username=me.username,
                    firstName=me.firstName,
                    lastName=me.lastName,
                    email=me.email,
                    phone=me.phone,
                    employeeId=me.employeeId,
                    role=me.role,
                    permissions=me.permissions,
                    status=me.status,
                    avatarColor=me.avatarColor,
                )
            )
        return result

    def get_user_by_id(self, user_id: int) -> UserResponse | None:
        if self.uow.users is None:
            raise RuntimeError("Unit of Work has not been started.")

        user = self.uow.users.get_by_id(user_id)
        if user is None:
            return None
        me = self.to_user_me(user)
        return UserResponse(
            id=me.id,
            username=me.username,
            firstName=me.firstName,
            lastName=me.lastName,
            email=me.email,
            phone=me.phone,
            employeeId=me.employeeId,
            role=me.role,
            permissions=me.permissions,
            status=me.status,
            avatarColor=me.avatarColor,
        )

    def create_user(
        self,
        req: UserCreateRequest,
        creator_user_id: int | None = None,
    ) -> UserResponse:
        if self.uow.users is None:
            raise RuntimeError("Unit of Work has not been started.")

        existing = self.uow.users.get_by_username(req.username)
        if existing:
            raise BusinessRuleViolation("Username already exists.")

        user = User(
            username=req.username,
            email=str(req.email),
            password_hash=hash_password(req.password),
            status="ACTIVE",
        )
        self.uow.users.add(user)

        # Assign role if role repo exists
        if getattr(self.uow, "roles", None) is not None and req.role:
            from app.application.identity.rbac_service import RBACService
            rbac = RBACService(self.uow)
            assigner_id = creator_user_id or 1
            rbac.assign_user_role(user.user_id, req.role, assigned_by_user_id=assigner_id)

        # Record audit event if available
        if getattr(self.uow, "audits", None) is not None:
            from app.application.audit.audit_service import AuditService
            AuditService(self.uow).record_event(
                actor_user_id=creator_user_id,
                action="User Created",
                resource_type="User",
                resource_id=user.user_id,
            )

        self.uow.commit()
        return self.get_user_by_id(user.user_id)

    def update_user(
        self,
        user_id: int,
        req: UserUpdateRequest,
        updater_user_id: int | None = None,
    ) -> UserResponse | None:
        if self.uow.users is None:
            raise RuntimeError("Unit of Work has not been started.")

        user = self.uow.users.get_by_id(user_id)
        if user is None:
            return None

        if req.email:
            user.email = str(req.email)
        if req.status:
            user.status = "ACTIVE" if req.status == "Active" else "DISABLED"
        if req.password:
            user.password_hash = hash_password(req.password)

        if getattr(self.uow, "roles", None) is not None and req.role:
            from app.application.identity.rbac_service import RBACService
            rbac = RBACService(self.uow)
            assigner_id = updater_user_id or 1
            rbac.assign_user_role(user.user_id, req.role, assigned_by_user_id=assigner_id)

        # Record audit event if available
        if getattr(self.uow, "audits", None) is not None:
            from app.application.audit.audit_service import AuditService
            AuditService(self.uow).record_event(
                actor_user_id=updater_user_id,
                action="User Updated",
                resource_type="User",
                resource_id=user.user_id,
            )

        self.uow.commit()
        return self.get_user_by_id(user.user_id)

    def delete_user(self, user_id: int, actor_user_id: int | None = None) -> None:
        if self.uow.users is None:
            raise RuntimeError("Unit of Work has not been started.")

        if getattr(self.uow, "roles", None) is not None:
            self.uow.roles.remove_user_roles(user_id)

        self.uow.users.delete(user_id)

        if getattr(self.uow, "audits", None) is not None:
            from app.application.audit.audit_service import AuditService
            AuditService(self.uow).record_event(
                actor_user_id=actor_user_id,
                action="User Deleted",
                resource_type="User",
                resource_id=user_id,
            )

        self.uow.commit()