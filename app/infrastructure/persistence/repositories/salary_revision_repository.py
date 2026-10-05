from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.compensation.repository import SalaryRevisionRepository as SalaryRevisionRepositoryContract
from app.infrastructure.persistence.models.salary_revision import SalaryRevisionModel


class SalaryRevisionRepository(SalaryRevisionRepositoryContract):
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, salary_revision_id: int) -> SalaryRevisionModel | None:
        return self.session.scalar(
            select(SalaryRevisionModel).where(
                SalaryRevisionModel.salary_revision_id == salary_revision_id
            )
        )

    def get_by_structure_and_number(
        self, salary_structure_id: int, revision_number: int
    ) -> SalaryRevisionModel | None:
        statement = select(SalaryRevisionModel).where(
            SalaryRevisionModel.salary_structure_id == salary_structure_id,
            SalaryRevisionModel.revision_number == revision_number,
        )
        return self.session.scalar(statement)

    def add(self, revision: SalaryRevisionModel) -> SalaryRevisionModel:
        self.session.add(revision)
        self.session.flush()
        return revision
