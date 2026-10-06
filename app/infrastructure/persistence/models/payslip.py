from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.models.base import Base


class Payslip(Base):
    """SQLAlchemy model for generated payslips."""

    __tablename__ = "payslips"

    payslip_id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    payroll_result_id: Mapped[int] = mapped_column(
        ForeignKey("payroll_results.payroll_result_id"),
        nullable=False,
    )

    payslip_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
    )

    generated_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id"),
        nullable=False,
    )

    generated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    document_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        default="",
    )
