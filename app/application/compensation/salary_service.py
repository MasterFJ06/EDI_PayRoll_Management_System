from decimal import Decimal
from typing import Any

from app.application.common.unit_of_work import UnitOfWork
from app.application.compensation.schemas import (
    SalaryStructureRequest,
    SalaryStructureResponse,
)
from app.application.payroll.engine import PayrollEngine
from app.domain.shared.exceptions import BusinessRuleViolation


class SalaryService:
    """Service for managing salary structures, assignments, and revisions."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def _build_structure_response(
        self,
        emp_code: str,
        basic: float,
        overrides: dict[str, Any] | None = None,
    ) -> SalaryStructureResponse:
        overrides = overrides or {}
        b_dec = Decimal(str(basic))
        defaults_allow = PayrollEngine.calculate_default_allowances(b_dec)
        defaults_ded = PayrollEngine.calculate_default_deductions(b_dec)

        hra = overrides.get("hra", float(defaults_allow["hra"]))
        da = overrides.get("da", float(defaults_allow["da"]))
        special = overrides.get("specialAllowance", overrides.get("special_allowance", float(defaults_allow["special_allowance"])))
        travel = overrides.get("travelAllowance", float(defaults_allow["travel_allowance"]))
        medical = overrides.get("medicalAllowance", float(defaults_allow["medical_allowance"]))
        other_all = overrides.get("otherAllowances", float(defaults_allow["other_allowances"]))

        pf = overrides.get("providentFund", float(defaults_ded["provident_fund"]))
        esi = overrides.get("esi", float(defaults_ded["esi"]))
        pt = overrides.get("professionalTax", float(defaults_ded["professional_tax"]))
        it = overrides.get("incomeTax", float(defaults_ded["income_tax"]))
        ins = overrides.get("insurance", float(defaults_ded["insurance"]))

        return SalaryStructureResponse(
            id=f"SS-{emp_code}",
            employeeId=emp_code,
            basic=basic,
            hra=hra,
            da=da,
            specialAllowance=special,
            travelAllowance=travel,
            medicalAllowance=medical,
            otherAllowances=other_all,
            providentFund=pf,
            professionalTax=pt,
            bonus=overrides.get("bonus", 0.0),
            overtimeRate=overrides.get("overtimeRate", 350.0),
            esi=esi,
            incomeTax=it,
            insurance=ins,
            loanDeduction=overrides.get("loanDeduction", 0.0),
            otherDeductions=overrides.get("otherDeductions", 0.0),
            effectiveFrom=overrides.get("effectiveFrom", "2026-04-01"),
            effectiveTo=overrides.get("effectiveTo", None),
            revisionNumber=overrides.get("revisionNumber", 2),
            status=overrides.get("status", "Active"),
        )

    def list_structures(self) -> list[SalaryStructureResponse]:
        """List all employee salary structures."""
        if getattr(self.uow, "employees", None) is None:
            raise RuntimeError("Unit of Work has not been started.")

        employees = self.uow.employees.get_all()
        # Default baseline basic values matching demo data
        default_basics = {
            "EMP001": 62000.0,
            "EMP002": 58000.0,
            "EMP003": 54000.0,
            "EMP004": 98000.0,
            "EMP005": 51000.0,
            "EMP006": 76000.0,
            "EMP007": 60000.0,
            "EMP008": 32000.0,
            "EMP009": 47000.0,
            "EMP010": 45000.0,
        }

        output: list[SalaryStructureResponse] = []
        for emp in employees:
            code = emp.employee_code
            basic = default_basics.get(code, 50000.0)

            # Check if assignment in DB
            if getattr(self.uow, "salaries", None) is not None:
                assignment = self.uow.salaries.get_assignment_for_employee(emp.employee_id)
                if assignment:
                    rev_comps = self.uow.salaries.get_revision_components(assignment.salary_revision_id)
                    for rc in rev_comps:
                        if rc.fixed_amount and rc.fixed_amount > 0:
                            basic = float(rc.fixed_amount)
                            break

            output.append(self._build_structure_response(code, basic))

        return output

    def get_structure_by_id(self, structure_id: str) -> SalaryStructureResponse | None:
        all_s = self.list_structures()
        for s in all_s:
            if s.id == structure_id or s.employeeId == structure_id:
                return s
        return None

    def create_structure(self, req: SalaryStructureRequest) -> SalaryStructureResponse:
        emp_code = req.employeeId or req.employee_id or "EMP001"
        return self._build_structure_response(
            emp_code=emp_code,
            basic=req.basic,
            overrides=req.model_dump(exclude_unset=True),
        )

    def update_structure(self, structure_id: str, patch: dict[str, Any]) -> SalaryStructureResponse | None:
        existing = self.get_structure_by_id(structure_id)
        if not existing:
            return None

        merged = existing.model_dump()
        merged.update(patch)
        emp_code = existing.employeeId
        basic = patch.get("basic", existing.basic)

        return self._build_structure_response(
            emp_code=emp_code,
            basic=basic,
            overrides=merged,
        )
