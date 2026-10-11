from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from app.api.dependencies.authorization import require_permission
from app.api.dependencies.unit_of_work import get_unit_of_work
from app.application.common.unit_of_work import UnitOfWork
from app.application.reporting.payroll_summary_service import (
    FinalizedPayrollSummaryService,
)
from app.application.reporting.payroll_results_report_service import (
    InvalidPayrollResultsCursor,
    PayrollResultsReportService,
)
from app.application.reporting.payroll_component_report_service import (
    InvalidPayrollComponentReportCursor,
    InvalidPayrollComponentReportFilters,
    PayrollComponentReportFilters,
    PayrollComponentReportService,
)
from app.application.reporting.employee_report_service import (
    EmployeeReportFilters,
    EmployeeReportService,
    InvalidEmployeeReportCursor,
)
from app.application.reporting.schemas import (
    EmployeePayrollResultReportPage,
    EmployeeReportPage,
    FinalizedPayrollSummaryResponse,
    PayrollComponentReportPage,
)
from app.infrastructure.persistence.models.user import User


router = APIRouter(prefix="/reports/payroll", tags=["Payroll Reports"])
employee_report_router = APIRouter(prefix="/reports", tags=["Employee Reports"])


@router.get(
    "/runs/{run_id}",
    response_model=FinalizedPayrollSummaryResponse,
)
def get_finalized_payroll_summary(
    run_id: Annotated[int, Path(gt=0)],
    current_user: Annotated[
        User, Depends(require_permission("report.payroll.read"))
    ],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> FinalizedPayrollSummaryResponse:
    summary = FinalizedPayrollSummaryService(uow).get(run_id)
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll Run not found.",
        )
    return summary


@router.get(
    "/runs/{run_id}/results",
    response_model=EmployeePayrollResultReportPage,
)
def get_finalized_payroll_results(
    run_id: Annotated[int, Path(gt=0)],
    current_user: Annotated[
        User, Depends(require_permission("report.payroll.read"))
    ],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: Annotated[str | None, Query(max_length=2048)] = None,
) -> EmployeePayrollResultReportPage:
    try:
        page = PayrollResultsReportService(uow).get_page(run_id, limit, cursor)
    except InvalidPayrollResultsCursor as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid payroll results cursor.",
        ) from exc
    if page is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll Run not found.",
        )
    return page


@router.get(
    "/runs/{run_id}/components",
    response_model=PayrollComponentReportPage,
)
def get_finalized_payroll_component_report(
    run_id: Annotated[int, Path(gt=0)],
    current_user: Annotated[
        User, Depends(require_permission("report.payroll.read"))
    ],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    employee_id: Annotated[int | None, Query(gt=0)] = None,
    salary_component_id: Annotated[int | None, Query(gt=0)] = None,
    component_type: Annotated[Literal["EARNING", "DEDUCTION"] | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: Annotated[str | None, Query(max_length=2048)] = None,
) -> PayrollComponentReportPage:
    try:
        page = PayrollComponentReportService(uow).get_page(
            run_id,
            limit,
            PayrollComponentReportFilters(
                employee_id=employee_id,
                salary_component_id=salary_component_id,
                component_type=component_type,
            ),
            cursor,
        )
    except InvalidPayrollComponentReportFilters as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except InvalidPayrollComponentReportCursor as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid Payroll Component Breakdown report cursor.",
        ) from exc
    if page is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll Run not found.",
        )
    return page


@employee_report_router.get(
    "/employees",
    response_model=EmployeeReportPage,
)
def get_employee_report(
    current_user: Annotated[
        User, Depends(require_permission("report.employee.read"))
    ],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: Annotated[str | None, Query(max_length=2048)] = None,
    employee_code: Annotated[str | None, Query(min_length=1, max_length=30)] = None,
    department_id: Annotated[int | None, Query(gt=0)] = None,
    designation_id: Annotated[int | None, Query(gt=0)] = None,
    employment_status: Annotated[
        Literal["ACTIVE", "INACTIVE", "TERMINATED"] | None, Query()
    ] = None,
) -> EmployeeReportPage:
    filters = EmployeeReportFilters(
        employee_code=employee_code,
        department_id=department_id,
        designation_id=designation_id,
        employment_status=employment_status,
    )
    try:
        return EmployeeReportService(uow).get_page(limit, filters, cursor)
    except InvalidEmployeeReportCursor as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid employee report cursor.",
        ) from exc
