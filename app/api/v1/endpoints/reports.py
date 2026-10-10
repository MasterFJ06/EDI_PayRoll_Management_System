from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.api.dependencies.authorization import require_permission
from app.api.dependencies.unit_of_work import get_unit_of_work
from app.application.common.unit_of_work import UnitOfWork
from app.application.reporting.payroll_summary_service import (
    FinalizedPayrollSummaryService,
)
from app.application.reporting.schemas import FinalizedPayrollSummaryResponse
from app.infrastructure.persistence.models.user import User


router = APIRouter(prefix="/reports/payroll", tags=["Payroll Reports"])


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
