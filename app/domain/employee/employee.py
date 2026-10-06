from datetime import date

from app.domain.shared.entity import Entity
from app.domain.shared.exceptions import BusinessRuleViolation


class Employee(Entity[int | None]):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    TERMINATED = "TERMINATED"

    VALID_STATUSES = {
        ACTIVE,
        INACTIVE,
        TERMINATED,
    }

    def __init__(
        self,
        employee_id: int | None,
        employee_code: str,
        first_name: str,
        last_name: str,
        department_id: int,
        designation_id: int,
        joining_date: date,
        employment_status: str = ACTIVE,
        user_id: int | None = None,
        manager_employee_id: int | None = None,
    ) -> None:
        normalized_code = employee_code.strip()
        normalized_first_name = first_name.strip()
        normalized_last_name = last_name.strip()
        normalized_status = employment_status.strip().upper()

        if not normalized_code:
            raise BusinessRuleViolation(
                "Employee code cannot be blank."
            )

        if not normalized_first_name:
            raise BusinessRuleViolation(
                "Employee first name cannot be blank."
            )

        if not normalized_last_name:
            raise BusinessRuleViolation(
                "Employee last name cannot be blank."
            )

        if department_id <= 0:
            raise BusinessRuleViolation(
                "Department ID must be positive."
            )

        if designation_id <= 0:
            raise BusinessRuleViolation(
                "Designation ID must be positive."
            )

        if normalized_status not in self.VALID_STATUSES:
            raise BusinessRuleViolation(
                "Employee employment status must be ACTIVE, INACTIVE, or TERMINATED."
            )

        if manager_employee_id is not None and employee_id is not None:
            if manager_employee_id == employee_id:
                raise BusinessRuleViolation(
                    "An employee cannot be their own manager."
                )

        super().__init__(employee_id)

        self.employee_code = normalized_code
        self.user_id = user_id
        self.first_name = normalized_first_name
        self.last_name = normalized_last_name
        self.department_id = department_id
        self.designation_id = designation_id
        self.manager_employee_id = manager_employee_id
        self.joining_date = joining_date
        self.employment_status = normalized_status

    def activate(self) -> None:
        self.employment_status = self.ACTIVE

    def deactivate(self) -> None:
        self.employment_status = self.INACTIVE

    def terminate(self) -> None:
        self.employment_status = self.TERMINATED

    def change_department(self, department_id: int) -> None:
        if department_id <= 0:
            raise BusinessRuleViolation(
                "Department ID must be positive."
            )

        self.department_id = department_id

    def change_designation(self, designation_id: int) -> None:
        if designation_id <= 0:
            raise BusinessRuleViolation(
                "Designation ID must be positive."
            )

        self.designation_id = designation_id

    def assign_manager(self, manager_employee_id: int | None) -> None:
        if (
            manager_employee_id is not None
            and self.id is not None
            and manager_employee_id == self.id
        ):
            raise BusinessRuleViolation(
                "An employee cannot be their own manager."
            )

        self.manager_employee_id = manager_employee_id