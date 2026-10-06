from sqlalchemy import ForeignKey, Index, Integer, PrimaryKeyConstraint
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.models.base import Base


_UNSIGNED_BIGINT = Integer().with_variant(mysql.BIGINT(unsigned=True), "mysql")


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (
        PrimaryKeyConstraint("role_id", "permission_id", name="pk_role_permissions"),
        Index("idx_role_permissions_permission", "permission_id"),
    )

    role_id: Mapped[int] = mapped_column(
        _UNSIGNED_BIGINT,
        ForeignKey(
            "roles.role_id",
            name="fk_role_permissions_role",
            ondelete="CASCADE",
            onupdate="RESTRICT",
        ),
        nullable=False,
    )
    permission_id: Mapped[int] = mapped_column(
        _UNSIGNED_BIGINT,
        ForeignKey(
            "permissions.permission_id",
            name="fk_role_permissions_permission",
            ondelete="CASCADE",
            onupdate="RESTRICT",
        ),
        nullable=False,
    )
