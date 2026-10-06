from app.application.common.unit_of_work import UnitOfWork
from app.application.identity.schemas import (
    RoleCreateRequest,
    RoleResponse,
    RoleUpdateRequest,
)
from app.domain.shared.exceptions import BusinessRuleViolation
from app.infrastructure.persistence.models.role import Role


class RoleService:
    """Service for managing system roles and permissions."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def list_roles(self) -> list[RoleResponse]:
        if self.uow.roles is None:
            raise RuntimeError("Unit of Work has not been started.")

        roles = self.uow.roles.get_all()
        result: list[RoleResponse] = []
        for r in roles:
            perms = self.uow.roles.get_role_permissions(r.role_id)
            perm_codes = [p.permission_code for p in perms]
            result.append(
                RoleResponse(
                    id=str(r.role_id),
                    name=r.role_name,
                    description=r.description,
                    isActive=r.is_active,
                    permissions=perm_codes,
                )
            )
        return result

    def get_role_by_id(self, role_id: int) -> RoleResponse | None:
        if self.uow.roles is None:
            raise RuntimeError("Unit of Work has not been started.")

        role = self.uow.roles.get_by_id(role_id)
        if role is None:
            return None

        perms = self.uow.roles.get_role_permissions(role.role_id)
        perm_codes = [p.permission_code for p in perms]
        return RoleResponse(
            id=str(role.role_id),
            name=role.role_name,
            description=role.description,
            isActive=role.is_active,
            permissions=perm_codes,
        )

    def create_role(self, req: RoleCreateRequest) -> RoleResponse:
        if self.uow.roles is None:
            raise RuntimeError("Unit of Work has not been started.")

        existing = self.uow.roles.get_by_name(req.name)
        if existing:
            raise BusinessRuleViolation(f"Role '{req.name}' already exists.")

        role = Role(
            role_name=req.name,
            description=req.description,
            is_active=True,
        )
        self.uow.roles.add(role)
        self.uow.commit()

        return self.get_role_by_id(role.role_id)

    def update_role(self, role_id: int, req: RoleUpdateRequest) -> RoleResponse | None:
        if self.uow.roles is None:
            raise RuntimeError("Unit of Work has not been started.")

        role = self.uow.roles.get_by_id(role_id)
        if role is None:
            return None

        if req.name:
            role.role_name = req.name
        if req.description is not None:
            role.description = req.description
        if req.isActive is not None:
            role.is_active = req.isActive

        self.uow.roles.update(role)
        self.uow.commit()

        return self.get_role_by_id(role.role_id)
