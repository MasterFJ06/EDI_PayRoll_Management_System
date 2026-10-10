from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request

from app.api.dependencies.authorization import require_permission
from app.api.dependencies.unit_of_work import get_unit_of_work
from app.application.common.unit_of_work import UnitOfWork
from app.application.workforce.overtime_policy_service import OvertimePolicyService
from app.application.workforce.overtime_schemas import OvertimePolicyCreateRequest, OvertimePolicyResponse
from app.infrastructure.persistence.models.user import User


router = APIRouter(prefix="/workforce/overtime-policy-versions", tags=["Workforce Overtime Policy"])


@router.post("", response_model=OvertimePolicyResponse, status_code=201)
def create_overtime_policy(
    body: OvertimePolicyCreateRequest,
    request: Request,
    current_user: Annotated[User, Depends(require_permission("workforce.overtime_policy.manage"))],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> OvertimePolicyResponse:
    return OvertimePolicyService(uow).create(
        body, current_user.user_id, getattr(request.state, "request_id", None)
    )


@router.get("/{policy_id}", response_model=OvertimePolicyResponse)
def get_overtime_policy(
    policy_id: Annotated[int, Path(gt=0)],
    current_user: Annotated[User, Depends(require_permission("workforce.overtime_policy.read"))],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> OvertimePolicyResponse:
    result = OvertimePolicyService(uow).get(policy_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Overtime policy version not found.")
    return result
