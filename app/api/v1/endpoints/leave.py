from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status

from app.api.dependencies.current_user import get_current_user
from app.api.dependencies.authorization import require_permission
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
    LeaveRequestReviewRequest,
    LeaveTypeCreateRequest,
    LeaveTypeResponse,
)
from app.infrastructure.persistence.models.user import User


router = APIRouter(prefix="", tags=["Leave Management"])


@router.post("/leave-types", response_model=LeaveTypeResponse, status_code=201)
def create_leave_type(
    request: LeaveTypeCreateRequest,
    current_user: Annotated[User, Depends(require_permission("workforce.leave_type.manage"))],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    http_request: Request,
) -> LeaveTypeResponse:
    return LeaveTypeService(uow).create(
        request, current_user.user_id, getattr(http_request.state, "request_id", None)
    )


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
    http_request: Request,
) -> LeaveRequestResponse:
    return LeaveRequestService(uow).create(
        request, current_user.user_id, getattr(http_request.state, "request_id", None)
    )


@router.post("/leave-requests/{leave_request_id}/approve", response_model=LeaveRequestResponse)
def approve_leave_request(
    leave_request_id: Annotated[int, Path(gt=0)],
    current_user: Annotated[User, Depends(require_permission("workforce.leave.approve"))],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    http_request: Request,
    request: LeaveRequestReviewRequest | None = None,
) -> LeaveRequestResponse:
    result = LeaveRequestService(uow).approve(
        leave_request_id,
        current_user.user_id,
        getattr(http_request.state, "request_id", None),
        request.review_comment if request else None,
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leave Request not found.")
    return result


@router.post("/leave-requests/{leave_request_id}/reject", response_model=LeaveRequestResponse)
def reject_leave_request(
    leave_request_id: Annotated[int, Path(gt=0)],
    current_user: Annotated[User, Depends(require_permission("workforce.leave.reject"))],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    http_request: Request,
    request: LeaveRequestReviewRequest | None = None,
) -> LeaveRequestResponse:
    result = LeaveRequestService(uow).reject(
        leave_request_id,
        current_user.user_id,
        getattr(http_request.state, "request_id", None),
        request.review_comment if request else None,
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leave Request not found.")
    return result


@router.post("/leave-requests/{leave_request_id}/cancel", response_model=LeaveRequestResponse)
def cancel_leave_request(
    leave_request_id: Annotated[int, Path(gt=0)],
    current_user: Annotated[User, Depends(require_permission("workforce.leave.cancel"))],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    http_request: Request,
) -> LeaveRequestResponse:
    result = LeaveRequestService(uow).cancel(
        leave_request_id,
        current_user.user_id,
        getattr(http_request.state, "request_id", None),
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leave Request not found.")
    return result
