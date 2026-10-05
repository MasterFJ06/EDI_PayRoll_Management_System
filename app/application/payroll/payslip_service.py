from app.application.common.unit_of_work import UnitOfWork
from app.application.payroll.schemas import PayslipCreateRequest, PayslipResponse
from app.domain.payroll.payslip import Payslip
from app.domain.shared.exceptions import BusinessRuleViolation
from app.infrastructure.persistence.models.payslip import PayslipModel


class PayslipService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def create(self, request: PayslipCreateRequest) -> PayslipResponse:
        if self.uow.payroll_results.get_by_id(request.payroll_result_id) is None:
            raise BusinessRuleViolation("Payroll result does not exist.")
        if self.uow.users.get_by_id(request.generated_by_user_id) is None:
            raise BusinessRuleViolation("Payslip generator user does not exist.")
        if self.uow.payslips.get_by_result_id(request.payroll_result_id) is not None:
            raise BusinessRuleViolation("A payslip already exists for this payroll result.")
        if self.uow.payslips.get_by_number(request.payslip_number) is not None:
            raise BusinessRuleViolation("Payslip number already exists.")
        payslip = Payslip(
            payslip_id=None,
            payroll_result_id=request.payroll_result_id,
            payslip_number=request.payslip_number,
            generated_by_user_id=request.generated_by_user_id,
            document_path=request.document_path,
        )
        model = PayslipModel(
            payroll_result_id=payslip.payroll_result_id,
            payslip_number=payslip.payslip_number,
            generated_by_user_id=payslip.generated_by_user_id,
            document_path=payslip.document_path,
        )
        self.uow.payslips.add(model)
        self.uow.commit()
        return PayslipResponse(
            payslip_id=model.payslip_id,
            payroll_result_id=model.payroll_result_id,
            payslip_number=model.payslip_number,
            generated_by_user_id=model.generated_by_user_id,
            document_path=model.document_path,
        )
