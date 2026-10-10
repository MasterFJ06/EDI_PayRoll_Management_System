from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status

from app.api.dependencies.authorization import require_permission
from app.api.dependencies.unit_of_work import get_unit_of_work
from app.api.schemas.payroll import PayrollRunCreateBody, PayslipCreateBody
from app.application.common.unit_of_work import UnitOfWork
from app.application.payroll.payroll_run_service import PayrollRunService
from app.application.payroll.payroll_processing_orchestrator import (
    PayrollProcessingOrchestrator,
)
from app.application.payroll.payroll_run_retry_service import PayrollRunRetryService
from app.application.payroll.payroll_run_finalization_service import (
    PayrollRunFinalizationService,
)
from app.application.payroll.schemas import (
    PayslipCreateRequest,
    PayslipResponse,
    PayrollRunCreateRequest,
    PayrollRunResponse,
)
from app.application.payroll.payslip_service import PayslipService
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


@router.post(
    "/runs/{run_id}/process",
    response_model=PayrollRunResponse,
)
def process_payroll_run(
    run_id: Annotated[int, Path(gt=0)],
    request: Request,
    current_user: Annotated[
        User, Depends(require_permission("payroll.run.process"))
    ],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> PayrollRunResponse:
    response = PayrollProcessingOrchestrator(uow).process(
        run_id,
        current_user.user_id,
        getattr(request.state, "request_id", None),
    )
    if response is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll Run not found.",
        )
    return response.payroll_run


@router.post(
    "/runs/{run_id}/retry",
    response_model=PayrollRunResponse,
)
def retry_payroll_run(
    run_id: Annotated[int, Path(gt=0)],
    request: Request,
    current_user: Annotated[
        User, Depends(require_permission("payroll.run.retry"))
    ],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> PayrollRunResponse:
    run = uow.payroll_runs.get_by_id(run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll Run not found.",
        )

    PayrollRunRetryService(uow).retry_failed_payroll_run(
        run_id,
        run.attempt_number,
        current_user.user_id,
        getattr(request.state, "request_id", None),
    )

    response = PayrollRunService(uow).get(run_id)
    if response is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll Run not found.",
        )
    return response


@router.post(
    "/runs/{run_id}/finalize",
    response_model=PayrollRunResponse,
)
def finalize_payroll_run(
    run_id: Annotated[int, Path(gt=0)],
    request: Request,
    current_user: Annotated[
        User, Depends(require_permission("payroll.run.finalize"))
    ],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> PayrollRunResponse:
    response = PayrollRunFinalizationService(uow).finalize(
        run_id,
        current_user.user_id,
        getattr(request.state, "request_id", None),
    )
    if response is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll Run not found.",
        )
    return response


@router.post(
    "/runs/{run_id}/results/{result_id}/payslip",
    response_model=PayslipResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_payslip(
    run_id: Annotated[int, Path(gt=0)],
    result_id: Annotated[int, Path(gt=0)],
    request_body: PayslipCreateBody,
    request: Request,
    current_user: Annotated[
        User, Depends(require_permission("payroll.payslip.create"))
    ],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> PayslipResponse:
    response = PayslipService(uow).generate(
        PayslipCreateRequest(
            payroll_run_id=run_id,
            payroll_result_id=result_id,
            payslip_number=request_body.payslip_number,
        ),
        current_user.user_id,
        getattr(request.state, "request_id", None),
    )
    if response is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll Run or Payroll Result not found.",
        )
    return response
