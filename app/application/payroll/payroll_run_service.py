from app.application.common.unit_of_work import UnitOfWork
from app.application.payroll.schemas import PayrollRunCreateRequest, PayrollRunResponse
from app.domain.payroll.payroll_run import PayrollRun
from app.domain.shared.exceptions import BusinessRuleViolation
from app.infrastructure.persistence.models.payroll_run import PayrollRunModel


class PayrollRunService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def create(self, request: PayrollRunCreateRequest) -> PayrollRunResponse:
        if self.uow.users.get_by_id(request.initiated_by_user_id) is None:
            raise BusinessRuleViolation("Initiating user does not exist.")
        if self.uow.payroll_runs.get_by_period(request.payroll_year, request.payroll_month):
            raise BusinessRuleViolation("A payroll run already exists for this period.")
        run = PayrollRun(
            payroll_run_id=None,
            payroll_year=request.payroll_year,
            payroll_month=request.payroll_month,
            initiated_by_user_id=request.initiated_by_user_id,
        )
        model = PayrollRunModel(
            payroll_year=run.payroll_year,
            payroll_month=run.payroll_month,
            status=run.status,
            initiated_by_user_id=run.initiated_by_user_id,
        )
        self.uow.payroll_runs.add(model)
        self.uow.commit()
        return PayrollRunResponse(
            payroll_run_id=model.payroll_run_id,
            payroll_year=model.payroll_year,
            payroll_month=model.payroll_month,
            status=model.status,
            initiated_by_user_id=model.initiated_by_user_id,
        )
