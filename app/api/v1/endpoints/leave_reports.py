from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies.authorization import require_permission
from app.api.dependencies.unit_of_work import get_unit_of_work
from app.application.common.unit_of_work import UnitOfWork
from app.application.reporting.leave_report_service import (
    InvalidLeaveReportCursor,
    InvalidLeaveReportFilters,
    LeaveAllocationReportFilters,
    LeaveBalanceReportFilters,
    LeaveReportService,
)
from app.application.reporting.schemas import (
    LeaveAllocationReportPage,
    LeaveBalanceReportPage,
)
from app.infrastructure.persistence.models.user import User


router = APIRouter(prefix="/reports/leave", tags=["Leave Reports"])


@router.get("/allocations", response_model=LeaveAllocationReportPage)
def get_leave_allocation_report(
    current_user: Annotated[User, Depends(require_permission("report.leave.read"))],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    employee_id: Annotated[int | None, Query(gt=0)] = None,
    department_id: Annotated[int | None, Query(gt=0)] = None,
    leave_type_id: Annotated[int | None, Query(gt=0)] = None,
    request_status: Annotated[
        Literal["PENDING", "APPROVED", "REJECTED", "CANCELLED"] | None,
        Query(alias="status"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: Annotated[str | None, Query(max_length=2048)] = None,
) -> LeaveAllocationReportPage:
    try:
        filters = LeaveAllocationReportFilters(
            date_from=date_from,
            date_to=date_to,
            employee_id=employee_id,
            department_id=department_id,
            leave_type_id=leave_type_id,
            status=request_status,
        )
        return LeaveReportService(uow).get_allocation_page(limit, filters, cursor)
    except InvalidLeaveReportFilters as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except InvalidLeaveReportCursor as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid Leave allocation report cursor.",
        ) from exc


@router.get("/balances", response_model=LeaveBalanceReportPage)
def get_leave_balance_report(
    current_user: Annotated[User, Depends(require_permission("report.leave.read"))],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    employee_id: Annotated[int | None, Query(gt=0)] = None,
    department_id: Annotated[int | None, Query(gt=0)] = None,
    leave_type_id: Annotated[int | None, Query(gt=0)] = None,
    balance_year: Annotated[int | None, Query(ge=0, le=65535)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: Annotated[str | None, Query(max_length=2048)] = None,
) -> LeaveBalanceReportPage:
    try:
        filters = LeaveBalanceReportFilters(
            employee_id=employee_id,
            department_id=department_id,
            leave_type_id=leave_type_id,
            balance_year=balance_year,
        )
        return LeaveReportService(uow).get_balance_page(limit, filters, cursor)
    except InvalidLeaveReportFilters as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except InvalidLeaveReportCursor as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid Leave balance report cursor.",
        ) from exc
