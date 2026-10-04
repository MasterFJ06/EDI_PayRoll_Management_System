from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies.current_user import get_current_user
from app.api.dependencies.unit_of_work import get_unit_of_work
from app.application.common.unit_of_work import UnitOfWork
from app.application.leave.leave_balance_service import LeaveBalanceService
from app.application.leave.leave_request_service import LeaveRequestService
from app.application.leave.leave_type_service import LeaveTypeService
from app.application.leave.schemas import (
    LeaveBalanceCreateRequest,
    LeaveBalanceResponse,
    LeaveRequestCreateRequest,
    LeaveRequestResponse,
    LeaveTypeCreateRequest,
    LeaveTypeResponse,
)
from app.infrastructure.persistence.models.user import User


router = APIRouter(prefix="", tags=["Leave Management"])


@router.post("/leave-types", response_model=LeaveTypeResponse, status_code=201)
def create_leave_type(
    request: LeaveTypeCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> LeaveTypeResponse:
    return LeaveTypeService(uow).create(request)


@router.post("/leave-balances", response_model=LeaveBalanceResponse, status_code=201)
def create_leave_balance(
    request: LeaveBalanceCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> LeaveBalanceResponse:
    return LeaveBalanceService(uow).create(request)


@router.post("/leave-requests", response_model=LeaveRequestResponse, status_code=201)
def create_leave_request(
    request: LeaveRequestCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> LeaveRequestResponse:
    return LeaveRequestService(uow).create(request)
