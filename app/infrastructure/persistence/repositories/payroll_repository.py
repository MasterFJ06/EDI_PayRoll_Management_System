from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models.payroll import (
    PayrollProcessingIssue,
    PayrollResult,
    PayrollResultComponent,
    PayrollRun,
)


class PayrollRepository:
    """Repository for payroll runs, results, components, and issues."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_runs(self) -> list[PayrollRun]:
        statement = select(PayrollRun).order_by(
            PayrollRun.payroll_year.desc(),
            PayrollRun.payroll_month.desc(),
        )
        return list(self.session.scalars(statement).all())

    def get_run_by_id(self, run_id: int) -> PayrollRun | None:
        statement = select(PayrollRun).where(PayrollRun.payroll_run_id == run_id)
        return self.session.scalar(statement)

    def get_run_by_period(self, year: int, month: int) -> PayrollRun | None:
        statement = select(PayrollRun).where(
            PayrollRun.payroll_year == year,
            PayrollRun.payroll_month == month,
        )
        return self.session.scalar(statement)

    def add_run(self, run: PayrollRun) -> PayrollRun:
        self.session.add(run)
        self.session.flush()
        return run

    def update_run(self, run: PayrollRun) -> PayrollRun:
        self.session.merge(run)
        self.session.flush()
        return run

    def get_results_by_run(self, run_id: int) -> list[PayrollResult]:
        statement = select(PayrollResult).where(
            PayrollResult.payroll_run_id == run_id
        )
        return list(self.session.scalars(statement).all())

    def get_result_by_id(self, result_id: int) -> PayrollResult | None:
        statement = select(PayrollResult).where(
            PayrollResult.payroll_result_id == result_id
        )
        return self.session.scalar(statement)

    def get_result_for_employee_and_run(
        self,
        run_id: int,
        employee_id: int,
    ) -> PayrollResult | None:
        statement = select(PayrollResult).where(
            PayrollResult.payroll_run_id == run_id,
            PayrollResult.employee_id == employee_id,
        )
        return self.session.scalar(statement)

    def get_all_results(self) -> list[PayrollResult]:
        statement = select(PayrollResult).order_by(
            PayrollResult.payroll_result_id.desc()
        )
        return list(self.session.scalars(statement).all())

    def add_result(self, result: PayrollResult) -> PayrollResult:
        self.session.add(result)
        self.session.flush()
        return result

    def add_result_component(
        self,
        component: PayrollResultComponent,
    ) -> PayrollResultComponent:
        self.session.add(component)
        self.session.flush()
        return component

    def get_result_components(
        self,
        result_id: int,
    ) -> list[PayrollResultComponent]:
        statement = select(PayrollResultComponent).where(
            PayrollResultComponent.payroll_result_id == result_id
        )
        return list(self.session.scalars(statement).all())

    def get_issues_by_run(
        self,
        run_id: int,
    ) -> list[PayrollProcessingIssue]:
        statement = select(PayrollProcessingIssue).where(
            PayrollProcessingIssue.payroll_run_id == run_id
        )
        return list(self.session.scalars(statement).all())

    def get_all_issues(self) -> list[PayrollProcessingIssue]:
        statement = select(PayrollProcessingIssue).order_by(
            PayrollProcessingIssue.payroll_issue_id.desc()
        )
        return list(self.session.scalars(statement).all())

    def get_issue_by_id(
        self,
        issue_id: int,
    ) -> PayrollProcessingIssue | None:
        statement = select(PayrollProcessingIssue).where(
            PayrollProcessingIssue.payroll_issue_id == issue_id
        )
        return self.session.scalar(statement)

    def add_issue(
        self,
        issue: PayrollProcessingIssue,
    ) -> PayrollProcessingIssue:
        self.session.add(issue)
        self.session.flush()
        return issue

    def update_issue(
        self,
        issue: PayrollProcessingIssue,
    ) -> PayrollProcessingIssue:
        self.session.merge(issue)
        self.session.flush()
        return issue
