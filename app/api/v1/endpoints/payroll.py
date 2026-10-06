from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.api.dependencies.authorization import require_permission
from app.api.dependencies.unit_of_work import get_unit_of_work
from app.api.schemas.payroll import PayrollRunCreateBody
from app.application.common.unit_of_work import UnitOfWork
from app.application.payroll.payroll_run_service import PayrollRunService
from app.application.payroll.schemas import PayrollRunCreateRequest, PayrollRunResponse
from app.infrastructure.persistence.models.user import User


router = APIRouter(prefix="/payroll", tags=["Payroll"])


@router.post(
    "/runs",
    response_model=PayrollRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_payroll_run(
    request: PayrollRunCreateBody,
    current_user: Annotated[
        User, Depends(require_permission("payroll.run.create"))
    ],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> PayrollRunResponse:
    command = PayrollRunCreateRequest(
        payroll_year=request.year,
        payroll_month=request.month,
        initiated_by_user_id=current_user.user_id,
    )
    return PayrollRunService(uow).create(command)


@router.get(
    "/runs/{run_id}",
    response_model=PayrollRunResponse,
)
def get_payroll_run(
    run_id: Annotated[int, Path(gt=0)],
    current_user: Annotated[
        User, Depends(require_permission("payroll.run.read"))
    ],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> PayrollRunResponse:
    response = PayrollRunService(uow).get(run_id)
    if response is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll Run not found.",
        )
    return response
