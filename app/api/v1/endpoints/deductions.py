from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies.current_user import get_current_user
from app.api.dependencies.unit_of_work import get_unit_of_work
from app.application.common.unit_of_work import UnitOfWork
from app.application.compensation.salary_service import SalaryService
from app.application.payroll.schemas import DeductionResponse, TaxRuleResponse
from app.infrastructure.persistence.models.user import User

router = APIRouter(
    prefix="",
    tags=["Deductions & Tax Rules"],
)


@router.get(
    "/deductions",
    response_model=list[DeductionResponse],
)
def list_deductions(
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> list[DeductionResponse]:
    salary_service = SalaryService(uow)
    structures = salary_service.list_structures()

    result: list[DeductionResponse] = []
    for ss in structures:
        # PF
        result.append(
            DeductionResponse(
                id=f"DED-{ss.employeeId}-PF",
                employeeId=ss.employeeId,
                payrollId=f"PR-2026-08-{ss.employeeId}",
                type="PF",
                calculationMethod="Percentage",
                amount=ss.providentFund,
                ruleApplied="12% of Basic",
                effectiveDate="2026-04-01",
                status="Active",
            )
        )
        # PT
        result.append(
            DeductionResponse(
                id=f"DED-{ss.employeeId}-PT",
                employeeId=ss.employeeId,
                payrollId=f"PR-2026-08-{ss.employeeId}",
                type="Professional Tax",
                calculationMethod="Flat",
                amount=ss.professionalTax,
                ruleApplied="Maharashtra PT Slab",
                effectiveDate="2026-04-01",
                status="Active",
            )
        )
        # Income Tax
        result.append(
            DeductionResponse(
                id=f"DED-{ss.employeeId}-IT",
                employeeId=ss.employeeId,
                payrollId=f"PR-2026-08-{ss.employeeId}",
                type="Income Tax",
                calculationMethod="Slab",
                amount=ss.incomeTax,
                ruleApplied="New Tax Regime FY26-27",
                effectiveDate="2026-04-01",
                status="Active",
            )
        )

    return result


@router.get(
    "/tax-rules",
    response_model=list[TaxRuleResponse],
)
def list_tax_rules(
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> list[TaxRuleResponse]:
    return [
        TaxRuleResponse(
            id="TR01",
            rule_name="Standard Deduction",
            regime="New & Old",
            slab_details="Flat Rs 75,000 deduction on salaried income",
            applicable_year="FY 2026-27",
            is_active=True,
        ),
        TaxRuleResponse(
            id="TR02",
            rule_name="Section 80C PF Deduction",
            regime="Old Regime",
            slab_details="Up to Rs 1,50,000 per financial year",
            applicable_year="FY 2026-27",
            is_active=True,
        ),
        TaxRuleResponse(
            id="TR03",
            rule_name="Professional Tax Exemption",
            regime="All",
            slab_details="Deductible under Section 16(iii)",
            applicable_year="FY 2026-27",
            is_active=True,
        ),
    ]
