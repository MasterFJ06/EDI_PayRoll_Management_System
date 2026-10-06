from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models.role import (
    Permission,
    Role,
    RolePermission,
    UserRole,
)


class RoleRepository:
    """Repository for roles and permissions persistence operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_all(self) -> list[Role]:
        statement = select(Role).order_by(Role.role_id.asc())
        return list(self.session.scalars(statement).all())

    def get_by_id(self, role_id: int) -> Role | None:
        statement = select(Role).where(Role.role_id == role_id)
        return self.session.scalar(statement)

    def get_by_name(self, role_name: str) -> Role | None:
        statement = select(Role).where(Role.role_name == role_name)
        return self.session.scalar(statement)

    def add(self, role: Role) -> Role:
        self.session.add(role)
        self.session.flush()
        return role

    def update(self, role: Role) -> Role:
        self.session.merge(role)
        self.session.flush()
        return role

    def get_user_roles(self, user_id: int) -> list[Role]:
        statement = (
            select(Role)
            .join(UserRole, UserRole.role_id == Role.role_id)
            .where(UserRole.user_id == user_id)
        )
        return list(self.session.scalars(statement).all())

    def assign_role(
        self,
        user_id: int,
        role_id: int,
        assigned_by_user_id: int,
    ) -> UserRole:
        user_role = UserRole(
            user_id=user_id,
            role_id=role_id,
            assigned_by_user_id=assigned_by_user_id,
        )
        self.session.merge(user_role)
        self.session.flush()
        return user_role

    def remove_user_roles(self, user_id: int) -> None:
        statement = delete(UserRole).where(UserRole.user_id == user_id)
        self.session.execute(statement)
        self.session.flush()

    def get_role_permissions(self, role_id: int) -> list[Permission]:
        statement = (
            select(Permission)
            .join(RolePermission, RolePermission.permission_id == Permission.permission_id)
            .where(RolePermission.role_id == role_id)
        )
        return list(self.session.scalars(statement).all())

    def get_all_permissions(self) -> list[Permission]:
        statement = select(Permission).order_by(Permission.permission_code.asc())
        return list(self.session.scalars(statement).all())
