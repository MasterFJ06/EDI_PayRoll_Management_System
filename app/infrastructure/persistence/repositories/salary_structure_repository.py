from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.compensation.repository import SalaryStructureRepository as SalaryStructureRepositoryContract
from app.infrastructure.persistence.models.salary_structure import SalaryStructureModel


class SalaryStructureRepository(SalaryStructureRepositoryContract):
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, salary_structure_id: int) -> SalaryStructureModel | None:
        return self.session.scalar(
            select(SalaryStructureModel).where(
                SalaryStructureModel.salary_structure_id == salary_structure_id
            )
        )

    def get_by_code(self, structure_code: str) -> SalaryStructureModel | None:
        return self.session.scalar(
            select(SalaryStructureModel).where(
                SalaryStructureModel.structure_code == structure_code
            )
        )

    def add(self, structure: SalaryStructureModel) -> SalaryStructureModel:
        self.session.add(structure)
        self.session.flush()
        return structure
