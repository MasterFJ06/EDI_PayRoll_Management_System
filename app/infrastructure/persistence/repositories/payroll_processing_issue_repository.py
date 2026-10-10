from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.payroll.repository import (
    PayrollProcessingIssueRepository as PayrollProcessingIssueRepositoryContract,
)
from app.infrastructure.persistence.models.payroll_processing_issue import (
    PayrollProcessingIssueModel,
)


class PayrollProcessingIssueRepository(PayrollProcessingIssueRepositoryContract):
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, payroll_issue_id: int) -> PayrollProcessingIssueModel | None:
        return self.session.scalar(
            select(PayrollProcessingIssueModel).where(
                PayrollProcessingIssueModel.payroll_issue_id == payroll_issue_id
            )
        )

    def list_by_run(self, payroll_run_id: int) -> list[PayrollProcessingIssueModel]:
        statement = (
            select(PayrollProcessingIssueModel)
            .where(PayrollProcessingIssueModel.payroll_run_id == payroll_run_id)
            .order_by(PayrollProcessingIssueModel.payroll_issue_id)
        )
        return list(self.session.scalars(statement).all())

    def add(
        self, issue: PayrollProcessingIssueModel
    ) -> PayrollProcessingIssueModel:
        self.session.add(issue)
        self.session.flush()
        return issue
