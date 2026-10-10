from app.application.common.unit_of_work import UnitOfWork
from app.application.reporting.schemas import FinalizedPayrollSummaryResponse
from app.domain.shared.exceptions import BusinessRuleViolation


class FinalizedPayrollSummaryService:
    """Reads summary totals from persisted Payroll Results."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def get(self, payroll_run_id: int) -> FinalizedPayrollSummaryResponse | None:
        run = self.uow.payroll_runs.get_by_id(payroll_run_id)
        if run is None:
            return None
        if run.status != "FINALIZED":
            raise BusinessRuleViolation(
                "Payroll summary is available only for a FINALIZED Payroll Run."
            )

        count, gross, deductions, net = self.uow.payroll_results.aggregate_by_run(
            payroll_run_id
        )
        if count == 0:
            # QA raises PAYROLL_QA_ZERO_ELIGIBLE_EMPLOYEES and prevents the run
            # from reaching PROCESSED/FINALIZED. Do not fabricate empty totals.
            raise BusinessRuleViolation(
                "A FINALIZED Payroll Run must contain at least one Payroll Result."
            )
        if gross is None or deductions is None or net is None:
            raise RuntimeError("Payroll Result aggregate returned incomplete totals.")

        return FinalizedPayrollSummaryResponse(
            payroll_run_id=run.payroll_run_id,
            payroll_year=run.payroll_year,
            payroll_month=run.payroll_month,
            status="FINALIZED",
            initiated_by_user_id=run.initiated_by_user_id,
            employee_result_count=count,
            total_gross_pay=gross,
            total_deductions=deductions,
            total_net_pay=net,
        )
