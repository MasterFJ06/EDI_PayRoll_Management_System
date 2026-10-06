from datetime import date
from app.application.common.unit_of_work import UnitOfWork
from app.application.employee.schemas import (
    EmployeeCreateRequest,
    EmployeeResponse,
    EmployeeUpdateRequest,
)
from app.domain.employee.employee import Employee
from app.domain.shared.exceptions import BusinessRuleViolation
from app.infrastructure.persistence.models.employee import Employee as EmployeeModel


class EmployeeService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def _to_response(self, model: EmployeeModel) -> EmployeeResponse:
        status_map = {
            "ACTIVE": "Active",
            "INACTIVE": "Suspended",
            "TERMINATED": "Terminated",
            "ON LEAVE": "On Leave",
        }
        status_str = status_map.get(model.employment_status.upper(), "Active")
        created_str = model.created_at.strftime("%Y-%m-%d") if getattr(model, "created_at", None) else ""
        updated_str = model.updated_at.strftime("%Y-%m-%d") if getattr(model, "updated_at", None) else ""
        joining_str = model.joining_date.strftime("%Y-%m-%d") if isinstance(model.joining_date, date) else str(model.joining_date)

        dept_str = f"D{model.department_id:02d}"
        desig_str = f"DS{model.designation_id:02d}"
        mgr_str = f"EMP{model.manager_employee_id:03d}" if model.manager_employee_id else None

        email = f"{model.first_name.lower()}.{model.last_name.lower()}@company.in"
        phone = "+91 98000 00000"

        # Check if user has email
        if getattr(self.uow, "users", None) is not None and model.user_id:
            u = self.uow.users.get_by_id(model.user_id)
            if u and getattr(u, "email", None):
                email = u.email

        return EmployeeResponse(
            employee_id=model.employee_id,
            employee_code=model.employee_code,
            user_id=model.user_id,
            first_name=model.first_name,
            last_name=model.last_name,
            department_id=model.department_id,
            designation_id=model.designation_id,
            manager_employee_id=model.manager_employee_id,
            joining_date=model.joining_date,
            employment_status=model.employment_status,
            id=model.employee_code,
            employeeCode=model.employee_code,
            firstName=model.first_name,
            lastName=model.last_name,
            email=email,
            phone=phone,
            dateOfBirth="1995-01-01",
            gender="Male",
            departmentId=dept_str,
            designationId=desig_str,
            managerId=mgr_str,
            employmentType="Full-Time",
            joiningDate=joining_str,
            employmentStatus=status_str,
            address="Pune, MH",
            emergencyContact="+91 99000 00000",
            createdDate=created_str,
            updatedDate=updated_str,
        )

    def create(self, request: EmployeeCreateRequest) -> EmployeeResponse:
        code = request.get_code().strip()
        first_name = request.get_first_name().strip()
        last_name = request.get_last_name().strip()
        dept_id = request.get_dept_id()
        desig_id = request.get_desig_id()
        joining = request.get_joining_date()

        if not code:
            raise BusinessRuleViolation("Employee code cannot be blank.")
        if not first_name:
            raise BusinessRuleViolation("First name cannot be blank.")
        if not last_name:
            raise BusinessRuleViolation("Last name cannot be blank.")

        existing_employee = self.uow.employees.get_by_code(code)
        if existing_employee is not None:
            raise BusinessRuleViolation("Employee code already exists.")

        if request.user_id is not None and getattr(self.uow, "users", None) is not None:
            user = self.uow.users.get_by_id(request.user_id)
            if user is None:
                raise BusinessRuleViolation("User does not exist.")

            existing_user_employee = self.uow.employees.get_by_user_id(request.user_id)
            if existing_user_employee is not None:
                raise BusinessRuleViolation("User is already assigned to an employee.")

        if getattr(self.uow, "departments", None) is not None:
            department = self.uow.departments.get_by_id(dept_id)
            if department is None:
                raise BusinessRuleViolation("Department does not exist.")

        if getattr(self.uow, "designations", None) is not None:
            designation = self.uow.designations.get_by_id(desig_id)
            if designation is None:
                raise BusinessRuleViolation("Designation does not exist.")

        if request.manager_employee_id is not None:
            manager = self.uow.employees.get_by_id(request.manager_employee_id)
            if manager is None:
                raise BusinessRuleViolation("Manager employee does not exist.")
            if manager.employment_status == "TERMINATED":
                raise BusinessRuleViolation("A terminated employee cannot be assigned as a manager.")

        employee_model = EmployeeModel(
            employee_code=code,
            user_id=request.user_id,
            first_name=first_name,
            last_name=last_name,
            department_id=dept_id,
            designation_id=desig_id,
            manager_employee_id=request.manager_employee_id,
            joining_date=joining,
            employment_status="ACTIVE",
        )

        self.uow.employees.add(employee_model)
        self.uow.commit()

        return self._to_response(employee_model)

    def list_all(self) -> list[EmployeeResponse]:
        if self.uow.employees is None:
            raise RuntimeError("Unit of Work has not been started.")

        employees = self.uow.employees.get_all()
        return [self._to_response(e) for e in employees]

    def get_by_id(self, employee_id: int | str) -> EmployeeResponse | None:
        if self.uow.employees is None:
            raise RuntimeError("Unit of Work has not been started.")

        if isinstance(employee_id, str):
            if employee_id.isdigit():
                emp = self.uow.employees.get_by_id(int(employee_id))
            else:
                emp = self.uow.employees.get_by_code(employee_id)
        else:
            emp = self.uow.employees.get_by_id(employee_id)

        if emp is None:
            return None
        return self._to_response(emp)

    def update(self, employee_id: int | str, request: EmployeeUpdateRequest) -> EmployeeResponse | None:
        if self.uow.employees is None:
            raise RuntimeError("Unit of Work has not been started.")

        if isinstance(employee_id, str) and not employee_id.isdigit():
            emp = self.uow.employees.get_by_code(employee_id)
        else:
            emp = self.uow.employees.get_by_id(int(employee_id))

        if emp is None:
            return None

        if request.first_name or request.firstName:
            emp.first_name = (request.first_name or request.firstName).strip()
        if request.last_name or request.lastName:
            emp.last_name = (request.last_name or request.lastName).strip()
        if request.department_id is not None:
            emp.department_id = request.department_id
        if request.designation_id is not None:
            emp.designation_id = request.designation_id
        if request.employment_status or request.employmentStatus:
            st = (request.employment_status or request.employmentStatus).upper()
            emp.employment_status = st

        self.uow.employees.update(emp)
        self.uow.commit()
        return self._to_response(emp)

    def delete(self, employee_id: int | str) -> None:
        if self.uow.employees is None:
            raise RuntimeError("Unit of Work has not been started.")

        if isinstance(employee_id, str) and not employee_id.isdigit():
            emp = self.uow.employees.get_by_code(employee_id)
            if emp:
                self.uow.employees.delete(emp.employee_id)
        else:
            self.uow.employees.delete(int(employee_id))
        self.uow.commit()