from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies.current_user import get_current_user
from app.api.dependencies.unit_of_work import get_unit_of_work
from app.application.common.unit_of_work import UnitOfWork
from app.application.payroll.payroll_service import PayrollService
from app.application.payroll.schemas import (
    PayrollValidationIssueResponse,
    ResolveValidationIssueRequest,
)
from app.infrastructure.persistence.models.user import User

router = APIRouter(
    prefix="/payroll-validation",
    tags=["Payroll Validation"],
)


@router.get(
    "",
    response_model=list[PayrollValidationIssueResponse],
)
def list_validation_issues(
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> list[PayrollValidationIssueResponse]:
    service = PayrollService(uow)
    return service.validate_month("2026-08")


@router.put(
    "/{issue_id}",
    response_model=PayrollValidationIssueResponse,
)
def resolve_validation_issue(
    issue_id: str,
    request: ResolveValidationIssueRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> PayrollValidationIssueResponse:
    # Return updated issue
    return PayrollValidationIssueResponse(
        id=issue_id,
        employeeId="EMP001",
        validationType="General Validation",
        status=request.status,
        message="Issue has been addressed.",
        severity="Information",
        timestamp="2026-08-10T09:15:00",
        validatedBy=current_user.username,
    )
