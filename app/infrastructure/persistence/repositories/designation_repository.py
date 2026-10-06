from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.organization.repository import (
    DesignationRepository as DesignationRepositoryContract,
)
from app.infrastructure.persistence.models.designation import Designation


class SQLAlchemyDesignationRepository(DesignationRepositoryContract):
    """SQLAlchemy repository for designation persistence operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, designation_id: int) -> Designation | None:
        statement = select(Designation).where(
            Designation.designation_id == designation_id
        )
        return self.session.scalar(statement)

    def get_by_code(self, designation_code: str) -> Designation | None:
        statement = select(Designation).where(
            Designation.designation_code == designation_code
        )
        return self.session.scalar(statement)

    def get_by_name(self, designation_name: str) -> Designation | None:
        statement = select(Designation).where(
            Designation.designation_name == designation_name
        )
        return self.session.scalar(statement)

    def get_all(self) -> list[Designation]:
        statement = select(Designation).order_by(Designation.designation_id.asc())
        return list(self.session.scalars(statement).all())

    def add(self, designation: Designation) -> Designation:
        self.session.add(designation)
        self.session.flush()
        return designation

    def update(self, designation: Designation) -> Designation:
        self.session.merge(designation)
        self.session.flush()
        return designation

    def delete(self, designation_id: int) -> None:
        desig = self.get_by_id(designation_id)
        if desig is not None:
            desig.status = "INACTIVE"
            self.session.flush()