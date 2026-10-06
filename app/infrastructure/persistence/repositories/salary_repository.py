from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models.salary import (
    EmployeeSalaryAssignment,
    SalaryComponent,
    SalaryRevision,
    SalaryRevisionComponent,
    SalaryStructure,
)


class SalaryRepository:
    """Repository for salary structures, components, revisions, and assignments."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_structures(self) -> list[SalaryStructure]:
        statement = select(SalaryStructure).order_by(
            SalaryStructure.salary_structure_id.asc()
        )
        return list(self.session.scalars(statement).all())

    def get_structure_by_id(self, structure_id: int) -> SalaryStructure | None:
        statement = select(SalaryStructure).where(
            SalaryStructure.salary_structure_id == structure_id
        )
        return self.session.scalar(statement)

    def get_structure_by_code(self, code: str) -> SalaryStructure | None:
        statement = select(SalaryStructure).where(
            SalaryStructure.structure_code == code
        )
        return self.session.scalar(statement)

    def add_structure(self, structure: SalaryStructure) -> SalaryStructure:
        self.session.add(structure)
        self.session.flush()
        return structure

    def update_structure(self, structure: SalaryStructure) -> SalaryStructure:
        self.session.merge(structure)
        self.session.flush()
        return structure

    def get_components(self) -> list[SalaryComponent]:
        statement = select(SalaryComponent).order_by(
            SalaryComponent.salary_component_id.asc()
        )
        return list(self.session.scalars(statement).all())

    def get_component_by_id(self, component_id: int) -> SalaryComponent | None:
        statement = select(SalaryComponent).where(
            SalaryComponent.salary_component_id == component_id
        )
        return self.session.scalar(statement)

    def get_component_by_code(self, code: str) -> SalaryComponent | None:
        statement = select(SalaryComponent).where(
            SalaryComponent.component_code == code
        )
        return self.session.scalar(statement)

    def add_component(self, component: SalaryComponent) -> SalaryComponent:
        self.session.add(component)
        self.session.flush()
        return component

    def get_latest_revision(self, structure_id: int) -> SalaryRevision | None:
        statement = (
            select(SalaryRevision)
            .where(SalaryRevision.salary_structure_id == structure_id)
            .order_by(SalaryRevision.revision_number.desc())
        )
        return self.session.scalars(statement).first()

    def get_revision_by_id(self, revision_id: int) -> SalaryRevision | None:
        statement = select(SalaryRevision).where(
            SalaryRevision.salary_revision_id == revision_id
        )
        return self.session.scalar(statement)

    def add_revision(self, revision: SalaryRevision) -> SalaryRevision:
        self.session.add(revision)
        self.session.flush()
        return revision

    def add_revision_component(
        self,
        rev_comp: SalaryRevisionComponent,
    ) -> SalaryRevisionComponent:
        self.session.add(rev_comp)
        self.session.flush()
        return rev_comp

    def get_revision_components(
        self,
        revision_id: int,
    ) -> list[SalaryRevisionComponent]:
        statement = (
            select(SalaryRevisionComponent)
            .where(SalaryRevisionComponent.salary_revision_id == revision_id)
        )
        return list(self.session.scalars(statement).all())

    def get_assignment_for_employee(
        self,
        employee_id: int,
    ) -> EmployeeSalaryAssignment | None:
        statement = (
            select(EmployeeSalaryAssignment)
            .where(EmployeeSalaryAssignment.employee_id == employee_id)
            .order_by(EmployeeSalaryAssignment.salary_assignment_id.desc())
        )
        return self.session.scalars(statement).first()

    def get_all_assignments(self) -> list[EmployeeSalaryAssignment]:
        statement = select(EmployeeSalaryAssignment).order_by(
            EmployeeSalaryAssignment.salary_assignment_id.asc()
        )
        return list(self.session.scalars(statement).all())

    def add_assignment(
        self,
        assignment: EmployeeSalaryAssignment,
    ) -> EmployeeSalaryAssignment:
        self.session.add(assignment)
        self.session.flush()
        return assignment

    def update_assignment(
        self,
        assignment: EmployeeSalaryAssignment,
    ) -> EmployeeSalaryAssignment:
        self.session.merge(assignment)
        self.session.flush()
        return assignment
