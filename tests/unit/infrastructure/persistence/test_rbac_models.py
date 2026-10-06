from sqlalchemy.dialects import mysql

from app.infrastructure.persistence.models.permission import Permission
from app.infrastructure.persistence.models.role import Role
from app.infrastructure.persistence.models.role_permission import RolePermission
from app.infrastructure.persistence.models.user_role import UserRole


def test_rbac_models_match_authoritative_mysql_columns_and_constraints() -> None:
    expected = {
        Role.__table__: {"role_id"},
        Permission.__table__: {"permission_id"},
        UserRole.__table__: {"user_id", "role_id", "assigned_by_user_id"},
        RolePermission.__table__: {"role_id", "permission_id"},
    }

    for table, unsigned_bigint_columns in expected.items():
        for column_name in unsigned_bigint_columns:
            column = table.c[column_name]
            assert column.type.compile(dialect=mysql.dialect()) == "BIGINT UNSIGNED"

    assert {constraint.name for constraint in Role.__table__.constraints} >= {
        "uq_roles_role_name"
    }
    assert {constraint.name for constraint in Permission.__table__.constraints} >= {
        "uq_permissions_permission_code"
    }
    assert {constraint.name for constraint in UserRole.__table__.constraints} >= {
        "pk_user_roles",
        "fk_user_roles_user",
        "fk_user_roles_role",
        "fk_user_roles_assigned_by",
    }
    assert {constraint.name for constraint in RolePermission.__table__.constraints} >= {
        "pk_role_permissions",
        "fk_role_permissions_role",
        "fk_role_permissions_permission",
    }
    assert {index.name for index in UserRole.__table__.indexes} == {
        "idx_user_roles_role"
    }
    assert {index.name for index in RolePermission.__table__.indexes} == {
        "idx_role_permissions_permission"
    }
