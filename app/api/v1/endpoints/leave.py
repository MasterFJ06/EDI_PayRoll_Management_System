from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies.current_user import get_current_user
from app.api.dependencies.unit_of_work import get_unit_of_work
from app.application.common.unit_of_work import UnitOfWork
from app.application.leave.leave_service import LeaveService
from app.application.leave.schemas import (
    LeaveApplyRequest,
    LeaveBalanceResponse,
    LeaveRequestResponse,
    LeaveReviewRequest,
)
from app.infrastructure.persistence.models.user import User

router = APIRouter(
    prefix="",
    tags=["Leaves"],
)


@router.get(
    "/leaves",
    response_model=list[LeaveRequestResponse],
)
def list_leaves(
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> list[LeaveRequestResponse]:
    service = LeaveService(uow)
    return service.list_leaves()


@router.get(
    "/leaves/{leave_id}",
    response_model=LeaveRequestResponse,
)
def get_leave(
    leave_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> LeaveRequestResponse:
    service = LeaveService(uow)
    req = service.get_leave_by_id(leave_id)
    if req is None:
        raise HTTPException(status_code=404, detail="Leave request not found.")
    return req


@router.post(
    "/leaves",
    response_model=LeaveRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def apply_leave(
    request: LeaveApplyRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> LeaveRequestResponse:
    service = LeaveService(uow)
    return service.apply_leave(request)


@router.put(
    "/leaves/{leave_id}/approve",
    response_model=LeaveRequestResponse,
)
def approve_leave(
    leave_id: str,
    request: LeaveReviewRequest | None = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)] = None,
) -> LeaveRequestResponse:
    service = LeaveService(uow)
    approver = request.approverId if request else None
    updated = service.approve_leave(leave_id, approver)
    if updated is None:
        raise HTTPException(status_code=404, detail="Leave request not found.")
    return updated


@router.put(
    "/leaves/{leave_id}/reject",
    response_model=LeaveRequestResponse,
)
def reject_leave(
    leave_id: str,
    request: LeaveReviewRequest | None = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)] = None,
) -> LeaveRequestResponse:
    service = LeaveService(uow)
    approver = request.approverId if request else None
    updated = service.reject_leave(leave_id, approver)
    if updated is None:
        raise HTTPException(status_code=404, detail="Leave request not found.")
    return updated


@router.put(
    "/leaves/{leave_id}",
    response_model=LeaveRequestResponse,
)
def cancel_or_update_leave(
    leave_id: str,
    request: LeaveReviewRequest | None = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)] = None,
) -> LeaveRequestResponse:
    service = LeaveService(uow)
    updated = service.cancel_leave(leave_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="Leave request not found.")
    return updated


@router.get(
    "/leave-balances",
    response_model=list[LeaveBalanceResponse],
)
def list_leave_balances(
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    employee_id: str | None = Query(None, alias="employee_id"),
) -> list[LeaveBalanceResponse]:
    service = LeaveService(uow)
    return service.list_balances(employee_id)
