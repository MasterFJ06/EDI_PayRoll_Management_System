from app.application.common.unit_of_work import UnitOfWork
from app.application.compensation.schemas import (
    SalaryStructureCreateRequest,
    SalaryStructureResponse,
)
from app.domain.compensation.salary_structure import SalaryStructure
from app.domain.shared.exceptions import BusinessRuleViolation
from app.infrastructure.persistence.models.salary_structure import SalaryStructureModel


class SalaryStructureService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def create(self, request: SalaryStructureCreateRequest) -> SalaryStructureResponse:
        structure = SalaryStructure(
            salary_structure_id=None,
            structure_code=request.structure_code,
            structure_name=request.structure_name,
            description=request.description,
            status=request.status,
        )
        if self.uow.salary_structures.get_by_code(structure.structure_code) is not None:
            raise BusinessRuleViolation("Salary structure code is already registered.")
        model = SalaryStructureModel(
            structure_code=structure.structure_code,
            structure_name=structure.structure_name,
            description=structure.description,
            status=structure.status,
        )
        self.uow.salary_structures.add(model)
        self.uow.commit()
        return SalaryStructureResponse(
            salary_structure_id=model.salary_structure_id,
            structure_code=model.structure_code,
            structure_name=model.structure_name,
            description=model.description,
            status=model.status,
        )
