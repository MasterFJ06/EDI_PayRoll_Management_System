from app.application.common.unit_of_work import UnitOfWork
from app.application.compensation.schemas import SalaryRevisionCreateRequest, SalaryRevisionResponse
from app.domain.compensation.salary_revision import SalaryRevision
from app.domain.shared.exceptions import BusinessRuleViolation
from app.infrastructure.persistence.models.salary_revision import SalaryRevisionModel


class SalaryRevisionService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def create(self, request: SalaryRevisionCreateRequest) -> SalaryRevisionResponse:
        if self.uow.salary_structures.get_by_id(request.salary_structure_id) is None:
            raise BusinessRuleViolation("Salary structure does not exist.")
        if self.uow.salary_revisions.get_by_structure_and_number(
            request.salary_structure_id, request.revision_number
        ) is not None:
            raise BusinessRuleViolation("Revision number already exists for this salary structure.")
        revision = SalaryRevision(
            salary_revision_id=None,
            salary_structure_id=request.salary_structure_id,
            revision_number=request.revision_number,
            effective_from=request.effective_from,
            effective_to=request.effective_to,
        )
        model = SalaryRevisionModel(
            salary_structure_id=revision.salary_structure_id,
            revision_number=revision.revision_number,
            effective_from=revision.effective_from,
            effective_to=revision.effective_to,
        )
        self.uow.salary_revisions.add(model)
        self.uow.commit()
        return SalaryRevisionResponse(
            salary_revision_id=model.salary_revision_id,
            salary_structure_id=model.salary_structure_id,
            revision_number=model.revision_number,
            effective_from=model.effective_from,
            effective_to=model.effective_to,
        )
