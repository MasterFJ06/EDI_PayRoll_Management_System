from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies.current_user import get_current_user
from app.api.dependencies.unit_of_work import get_unit_of_work
from app.application.common.unit_of_work import UnitOfWork
from app.application.payroll.payroll_service import PayrollService
from app.application.payroll.schemas import (
    PayrollRecordResponse,
    PayrollValidationIssueResponse,
    ProcessPayrollRequest,
    ValidatePayrollRequest,
)
from app.infrastructure.persistence.models.user import User

router = APIRouter(
    prefix="/payroll",
    tags=["Payroll Processing"],
)


@router.get(
    "",
    response_model=list[PayrollRecordResponse],
)
def list_payroll(
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> list[PayrollRecordResponse]:
    service = PayrollService(uow)
    return service.list_payroll()


@router.get(
    "/{record_id}",
    response_model=PayrollRecordResponse,
)
def get_payroll(
    record_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> PayrollRecordResponse:
    service = PayrollService(uow)
    record = service.get_payroll_by_id(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Payroll record not found.")
    return record


@router.post(
    "/process",
    response_model=int,
)
def process_payroll(
    request: ProcessPayrollRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> int:
    service = PayrollService(uow)
    month_str = request.get_month_str()
    return service.process_month(month_str, user_id=current_user.user_id)


@router.post(
    "/validate",
    response_model=list[PayrollValidationIssueResponse],
)
def validate_payroll(
    request: ValidatePayrollRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> list[PayrollValidationIssueResponse]:
    service = PayrollService(uow)
    month_str = request.get_month_str()
    return service.validate_month(month_str)


@router.post(
    "/{record_id}/approve",
    response_model=PayrollRecordResponse,
)
def approve_payroll(
    record_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> PayrollRecordResponse:
    service = PayrollService(uow)
    record = service.approve_payroll(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Payroll record not found.")
    return record
