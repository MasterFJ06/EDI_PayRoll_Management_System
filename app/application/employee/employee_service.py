from app.application.common.unit_of_work import UnitOfWork
from app.application.employee.schemas import (
    EmployeeCreateRequest,
    EmployeeResponse,
)
from app.domain.employee.employee import Employee
from app.domain.shared.exceptions import BusinessRuleViolation
from app.infrastructure.persistence.models.employee import Employee as EmployeeModel


class EmployeeService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def create(self, request: EmployeeCreateRequest) -> EmployeeResponse:
        employee_code = request.employee_code.strip()

        # ---------------------------------------------------------
        # 1. Employee code must be unique
        # ---------------------------------------------------------
        existing_employee = self.uow.employees.get_by_code(employee_code)

        if existing_employee is not None:
            raise BusinessRuleViolation(
                "Employee code already exists."
            )

        # ---------------------------------------------------------
        # 2. Validate user assignment
        # ---------------------------------------------------------
        if request.user_id is not None:
            user = self.uow.users.get_by_id(request.user_id)

            if user is None:
                raise BusinessRuleViolation(
                    "User does not exist."
                )

            existing_user_employee = (
                self.uow.employees.get_by_user_id(request.user_id)
            )

            if existing_user_employee is not None:
                raise BusinessRuleViolation(
                    "User is already assigned to an employee."
                )

        # ---------------------------------------------------------
        # 3. Validate department
        # ---------------------------------------------------------
        department = self.uow.departments.get_by_id(
            request.department_id
        )

        if department is None:
            raise BusinessRuleViolation(
                "Department does not exist."
            )

        # ---------------------------------------------------------
        # 4. Validate designation
        # ---------------------------------------------------------
        designation = self.uow.designations.get_by_id(
            request.designation_id
        )

        if designation is None:
            raise BusinessRuleViolation(
                "Designation does not exist."
            )

        # ---------------------------------------------------------
        # 5. Validate manager
        # ---------------------------------------------------------
        if request.manager_employee_id is not None:
            manager = self.uow.employees.get_by_id(
                request.manager_employee_id
            )

            if manager is None:
                raise BusinessRuleViolation(
                    "Manager employee does not exist."
                )

            if manager.employment_status == Employee.TERMINATED:
                raise BusinessRuleViolation(
                    "A terminated employee cannot be assigned as a manager."
                )

        # ---------------------------------------------------------
        # 6. Domain validation
        # ---------------------------------------------------------
        employee = Employee(
            employee_id=None,
            employee_code=request.employee_code,
            user_id=request.user_id,
            first_name=request.first_name,
            last_name=request.last_name,
            department_id=request.department_id,
            designation_id=request.designation_id,
            manager_employee_id=request.manager_employee_id,
            joining_date=request.joining_date,
        )

        # ---------------------------------------------------------
        # 7. Create persistence model
        # ---------------------------------------------------------
        employee_model = EmployeeModel(
            employee_code=employee.employee_code,
            user_id=employee.user_id,
            first_name=employee.first_name,
            last_name=employee.last_name,
            department_id=employee.department_id,
            designation_id=employee.designation_id,
            manager_employee_id=employee.manager_employee_id,
            joining_date=employee.joining_date,
            employment_status=employee.employment_status,
        )

        self.uow.employees.add(employee_model)
        self.uow.commit()

        return EmployeeResponse(
            employee_id=employee_model.employee_id,
            employee_code=employee_model.employee_code,
            user_id=employee_model.user_id,
            first_name=employee_model.first_name,
            last_name=employee_model.last_name,
            department_id=employee_model.department_id,
            designation_id=employee_model.designation_id,
            manager_employee_id=employee_model.manager_employee_id,
            joining_date=employee_model.joining_date,
            employment_status=employee_model.employment_status,
        )