from sqlalchemy import create_engine, delete, update
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models.role import Role
from app.infrastructure.persistence.models.role_permission import RolePermission
from app.infrastructure.persistence.models.user_role import UserRole
from app.infrastructure.persistence.repositories.authorization_repository import (
    AuthorizationRepository,
)


def test_permission_query_respects_role_permission_chain_and_revocations() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE roles (role_id INTEGER PRIMARY KEY, is_active BOOLEAN NOT NULL)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE permissions (permission_id INTEGER PRIMARY KEY, permission_code VARCHAR(100) NOT NULL)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE user_roles (user_id INTEGER NOT NULL, role_id INTEGER NOT NULL, assigned_by_user_id INTEGER NOT NULL, assigned_at DATETIME, PRIMARY KEY (user_id, role_id))"
        )
        connection.exec_driver_sql(
            "CREATE TABLE role_permissions (role_id INTEGER NOT NULL, permission_id INTEGER NOT NULL, PRIMARY KEY (role_id, permission_id))"
        )
        connection.exec_driver_sql(
            "INSERT INTO roles VALUES (1, TRUE), (2, TRUE)"
        )
        connection.exec_driver_sql(
            "INSERT INTO permissions VALUES (10, 'payroll.run.create'), (11, 'payroll.run.read')"
        )
        connection.exec_driver_sql(
            "INSERT INTO user_roles VALUES (41, 1, 41, CURRENT_TIMESTAMP), (41, 2, 41, CURRENT_TIMESTAMP)"
        )
        connection.exec_driver_sql(
            "INSERT INTO role_permissions VALUES (1, 10), (1, 11), (2, 11)"
        )

    with Session(engine) as session:
        repository = AuthorizationRepository(session)
        assert repository.has_permission(41, "payroll.run.create")
        assert repository.has_permission(41, "payroll.run.read")
        assert not repository.has_permission(41, "payroll.run.retry")

        session.execute(
            delete(RolePermission).where(
                RolePermission.role_id == 1,
                RolePermission.permission_id == 10,
            )
        )
        session.flush()
        assert not repository.has_permission(41, "payroll.run.create")

        assert repository.has_permission(41, "payroll.run.read")

        session.execute(update(Role).where(Role.role_id == 1).values(is_active=False))
        session.flush()
        assert repository.has_permission(41, "payroll.run.read")

        session.execute(
            delete(UserRole).where(UserRole.user_id == 41, UserRole.role_id == 2)
        )
        session.flush()
        assert not repository.has_permission(41, "payroll.run.read")

    engine.dispose()
