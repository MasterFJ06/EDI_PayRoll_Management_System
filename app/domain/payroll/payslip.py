from datetime import datetime

from app.domain.shared.entity import Entity
from app.domain.shared.exceptions import BusinessRuleViolation


class Payslip(Entity[int | None]):
    def __init__(
        self,
        payslip_id: int | None,
        payroll_result_id: int,
        payslip_number: str,
        generated_by_user_id: int,
        document_path: str,
        generated_at: datetime | None = None,
    ) -> None:
        if payroll_result_id <= 0 or generated_by_user_id <= 0:
            raise BusinessRuleViolation("Payroll result and generator user IDs must be positive.")
        super().__init__(payslip_id)
        self.payroll_result_id = payroll_result_id
        self.payslip_number = payslip_number
        self.generated_by_user_id = generated_by_user_id
        self.generated_at = generated_at
        self.document_path = document_path
