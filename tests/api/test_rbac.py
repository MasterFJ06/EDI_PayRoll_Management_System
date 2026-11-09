from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient

from app.api.dependencies.unit_of_work import get_unit_of_work
from app.application.identity.rbac_service import (
    RBACService,
    STANDARD_PERMISSIONS,
    STANDARD_ROLES,
    normalize_role_name,
)
from app.application.identity.schemas import (
    UserCreateRequest,
    UserRegistrationRequest,
    UserUpdateRequest,
)
from app.application.identity.user_service import UserService
from app.domain.shared.exceptions import BusinessRuleViolation
from app.infrastructure.persistence.models.role import (
    Permission,
    Role,
    RolePermission,
    UserRole,
)
from app.infrastructure.persistence.models.user import User
from app.infrastructure.security.jwt import create_access_token
from app.infrastructure.security.password import hash_password, verify_password
from app.main import app


class InMemoryUserRepository:
    def __init__(self):
        self.users: dict[int, User] = {}
        self.next_id = 1

    def get_all(self) -> list[User]:
        return list(self.users.values())

    def get_by_id(self, user_id: int) -> User | None:
        return self.users.get(user_id)

    def get_by_username(self, username: str) -> User | None:
        return next((u for u in self.users.values() if u.username == username), None)

    def get_by_email(self, email: str) -> User | None:
        return next((u for u in self.users.values() if u.email == email), None)

    def add(self, user: User) -> User:
        if not hasattr(user, "user_id") or not user.user_id:
            user.user_id = self.next_id
            self.next_id += 1
        self.users[user.user_id] = user
        return user

    def update(self, user: User) -> User:
        self.users[user.user_id] = user
        return user

    def delete(self, user_id: int) -> None:
        self.users.pop(user_id, None)


class InMemoryRoleRepository:
    def __init__(self):
        self.roles: dict[int, Role] = {}
        self.permissions: dict[int, Permission] = {}
        self.user_roles: list[UserRole] = []
        self.role_permissions: list[RolePermission] = []
        self.next_role_id = 1
        self.next_perm_id = 1

    def get_all(self) -> list[Role]:
        return list(self.roles.values())

    def get_by_id(self, role_id: int) -> Role | None:
        return self.roles.get(role_id)

    def get_by_name(self, role_name: str) -> Role | None:
        canon = normalize_role_name(role_name)
        return next((r for r in self.roles.values() if r.role_name.lower() in (role_name.lower(), canon.lower())), None)

    def add(self, role: Role) -> Role:
        if not getattr(role, "role_id", None):
            role.role_id = self.next_role_id
            self.next_role_id += 1
        self.roles[role.role_id] = role
        return role

    def update(self, role: Role) -> Role:
        self.roles[role.role_id] = role
        return role

    def get_all_permissions(self) -> list[Permission]:
        return list(self.permissions.values())

    def get_permission_by_code(self, permission_code: str) -> Permission | None:
        return next((p for p in self.permissions.values() if p.permission_code == permission_code), None)

    def add_permission(self, permission: Permission) -> Permission:
        if not getattr(permission, "permission_id", None):
            permission.permission_id = self.next_perm_id
            self.next_perm_id += 1
        self.permissions[permission.permission_id] = permission
        return permission

    def get_role_permission(self, role_id: int, permission_id: int) -> RolePermission | None:
        return next((rp for rp in self.role_permissions if rp.role_id == role_id and rp.permission_id == permission_id), None)

    def add_role_permission(self, role_id: int, permission_id: int) -> RolePermission:
        existing = self.get_role_permission(role_id, permission_id)
        if existing:
            return existing
        rp = RolePermission(role_id=role_id, permission_id=permission_id)
        self.role_permissions.append(rp)
        return rp

    def get_role_permissions(self, role_id: int) -> list[Permission]:
        perm_ids = [rp.permission_id for rp in self.role_permissions if rp.role_id == role_id]
        return [self.permissions[pid] for pid in perm_ids if pid in self.permissions]

    def get_user_roles(self, user_id: int) -> list[Role]:
        role_ids = [ur.role_id for ur in self.user_roles if ur.user_id == user_id]
        return [self.roles[rid] for rid in role_ids if rid in self.roles]

    def assign_role(self, user_id: int, role_id: int, assigned_by_user_id: int) -> UserRole:
        self.remove_user_role(user_id, role_id)
        ur = UserRole(user_id=user_id, role_id=role_id, assigned_by_user_id=assigned_by_user_id)
        self.user_roles.append(ur)
        return ur

    def remove_user_roles(self, user_id: int) -> None:
        self.user_roles = [ur for ur in self.user_roles if ur.user_id != user_id]

    def remove_user_role(self, user_id: int, role_id: int) -> None:
        self.user_roles = [ur for ur in self.user_roles if not (ur.user_id == user_id and ur.role_id == role_id)]

    def get_user_permissions(self, user_id: int) -> list[Permission]:
        roles = self.get_user_roles(user_id)
        perms: list[Permission] = []
        seen = set()
        for r in roles:
            for p in self.get_role_permissions(r.role_id):
                if p.permission_code not in seen:
                    seen.add(p.permission_code)
                    perms.append(p)
        return perms


class FakeAuditRepo:
    def __init__(self):
        self.events = []

    def add(self, ev):
        self.events.append(ev)
        return ev

    def get_all(self):
        return self.events


class FakeRBACUnitOfWork:
    def __init__(self):
        self.users = InMemoryUserRepository()
        self.roles = InMemoryRoleRepository()
        self.audits = FakeAuditRepo()
        self.employees = None
        self.session = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def commit(self):
        pass

    def rollback(self):
        pass


@pytest.fixture
def rbac_uow():
    uow = FakeRBACUnitOfWork()
    # Initialize standard RBAC
    rbac = RBACService(uow)
    rbac.init_rbac()

    # Create admin user (id=1)
    admin_user = User(
        user_id=1,
        username="admin.test",
        email="admin@company.in",
        password_hash=hash_password("AdminSecure123!"),
        status="ACTIVE",
    )
    uow.users.add(admin_user)
    rbac.assign_user_role(1, "System Administrator", assigned_by_user_id=1)

    # Create member user (id=2)
    member_user = User(
        user_id=2,
        username="member.test",
        email="member@company.in",
        password_hash=hash_password("MemberSecure123!"),
        status="ACTIVE",
    )
    uow.users.add(member_user)
    rbac.assign_user_role(2, "Employee", assigned_by_user_id=1)

    return uow


@pytest.fixture
def rbac_client(rbac_uow):
    app.dependency_overrides[get_unit_of_work] = lambda: rbac_uow
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


# ============================================================================
# 1. RBAC Initialization Tests
# ============================================================================

def test_rbac_initialization_idempotency(rbac_uow):
    """Running RBAC initialization multiple times produces identical state with zero duplicates."""
    rbac = RBACService(rbac_uow)

    # First run happened in fixture
    assert len(rbac_uow.roles.get_all()) == len(STANDARD_ROLES)
    assert len(rbac_uow.roles.get_all_permissions()) == len(STANDARD_PERMISSIONS)

    # Second run
    summary = rbac.init_rbac()
    assert summary["roles_created"] == 0
    assert summary["permissions_created"] == 0
    assert summary["mappings_created"] == 0
    assert len(rbac_uow.roles.get_all()) == len(STANDARD_ROLES)
    assert len(rbac_uow.roles.get_all_permissions()) == len(STANDARD_PERMISSIONS)


def test_password_hashing_and_verification():
    """Passwords are encrypted with recommended Argon2id and plain passwords never match."""
    plain = "SuperSecretPassword123!"
    hashed = hash_password(plain)

    assert hashed != plain
    assert "$argon2id$" in hashed or "$2b$" in hashed
    assert verify_password(plain, hashed) is True
    assert verify_password("WrongPassword123!", hashed) is False


# ============================================================================
# 2. Public Registration & Role Assignment Tests
# ============================================================================

def test_public_registration_defaults_to_member_role(rbac_uow):
    """Public user registration assigns the default Employee/Member role."""
    service = UserService(rbac_uow)
    req = UserRegistrationRequest(
        username="newuser",
        email="newuser@company.in",
        password="ValidPassword123!",
    )
    resp = service.register(req)
    assert resp.user_id is not None
    assert resp.status == "ACTIVE"

    # Verify role in user_roles
    rbac = RBACService(rbac_uow)
    assert rbac.get_user_role_name(resp.user_id) == "Employee"


def test_public_registration_cannot_escalate_to_admin(rbac_client, rbac_uow):
    """Submitting extra role fields in public registration is ignored."""
    payload = {
        "username": "sneaky.user",
        "email": "sneaky@company.in",
        "password": "Password123!",
        "role": "System Administrator",
    }
    res = rbac_client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 201

    created_user = rbac_uow.users.get_by_username("sneaky.user")
    assert created_user is not None

    rbac = RBACService(rbac_uow)
    assert rbac.get_user_role_name(created_user.user_id) == "Employee"


# ============================================================================
# 3. Endpoint Authorization & Access Control Tests
# ============================================================================

def test_unauthenticated_request_is_rejected(rbac_client):
    """Requests without a token receive 401 Unauthorized."""
    res = rbac_client.get("/api/v1/users")
    assert res.status_code == 401


def test_admin_can_access_users_endpoint(rbac_client):
    """System Administrator can access /api/v1/users."""
    token = create_access_token(user_id=1, username="admin.test")
    res = rbac_client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 2


def test_member_is_forbidden_from_users_endpoint(rbac_client):
    """A Member receiving a 403 Forbidden when attempting to access /api/v1/users."""
    token = create_access_token(user_id=2, username="member.test")
    res = rbac_client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403
    assert "users.manage" in res.json().get("detail", "")


def test_member_cannot_create_or_delete_users(rbac_client):
    """A Member cannot create or delete users."""
    token = create_access_token(user_id=2, username="member.test")
    headers = {"Authorization": f"Bearer {token}"}

    create_res = rbac_client.post("/api/v1/users", json={
        "username": "hacker", "email": "hacker@test.in", "password": "Password123!", "role": "System Administrator"
    }, headers=headers)
    assert create_res.status_code == 403

    del_res = rbac_client.delete("/api/v1/users/1", headers=headers)
    assert del_res.status_code == 403


def test_admin_can_create_user_and_assign_role(rbac_client, rbac_uow):
    """Admin can create new user accounts and specify a legitimate role."""
    token = create_access_token(user_id=1, username="admin.test")
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "username": "hr.manager",
        "email": "hr@company.in",
        "password": "SecurePassword123!",
        "role": "HR",
        "firstName": "HR",
        "lastName": "Manager",
    }
    res = rbac_client.post("/api/v1/users", json=payload, headers=headers)
    assert res.status_code == 201
    created = res.json()
    assert created["role"] == "HR"

    # Verify backend RBAC assignment
    new_user = rbac_uow.users.get_by_username("hr.manager")
    rbac = RBACService(rbac_uow)
    assert rbac.get_user_role_name(new_user.user_id) == "HR"


def test_admin_cannot_delete_own_account(rbac_client):
    """Admin is protected from accidentally deleting their own user account."""
    token = create_access_token(user_id=1, username="admin.test")
    res = rbac_client.delete("/api/v1/users/1", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 400
    assert "Cannot delete your own user account" in res.json()["detail"]


def test_member_cannot_modify_roles(rbac_client):
    """A member cannot create or modify roles."""
    token = create_access_token(user_id=2, username="member.test")
    headers = {"Authorization": f"Bearer {token}"}

    res = rbac_client.post("/api/v1/roles", json={"name": "CustomRole", "description": "test"}, headers=headers)
    assert res.status_code == 403


def test_role_assignment_persists_assigned_by_user_id(rbac_uow):
    """Assigning roles respects the assigned_by_user_id database constraint."""
    rbac = RBACService(rbac_uow)
    ur = rbac.assign_user_role(user_id=2, role_name="Manager", assigned_by_user_id=1)
    assert ur.user_id == 2
    assert ur.assigned_by_user_id == 1
    assert rbac.get_user_role_name(2) == "Manager"


def test_bootstrap_admin_validators():
    """Verify input validation for admin bootstrap script."""
    from scripts.bootstrap_admin import validate_username, validate_email, validate_password

    # Valid inputs should not raise
    validate_username("sysadmin")
    validate_email("admin@epms.org")
    validate_password("SecureAdminPassword123!")

    # Invalid usernames
    with pytest.raises(ValueError):
        validate_username("ab")
    with pytest.raises(ValueError):
        validate_username("bad user with spaces")

    # Invalid emails
    with pytest.raises(ValueError):
        validate_email("invalid-email")
    with pytest.raises(ValueError):
        validate_email("admin@")

    # Short passwords
    with pytest.raises(ValueError):
        validate_password("short")

