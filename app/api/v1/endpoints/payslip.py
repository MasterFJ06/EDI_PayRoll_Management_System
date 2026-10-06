from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import Response

from app.api.dependencies.current_user import get_current_user
from app.api.dependencies.unit_of_work import get_unit_of_work
from app.application.common.unit_of_work import UnitOfWork
from app.application.payroll.payslip_service import PayslipService
from app.application.payroll.schemas import CreatePayslipRequest, PayslipResponse
from app.infrastructure.persistence.models.user import User

router = APIRouter(
    prefix="/payslips",
    tags=["Payslips"],
)


@router.get(
    "",
    response_model=list[PayslipResponse],
)
def list_payslips(
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> list[PayslipResponse]:
    service = PayslipService(uow)
    return service.list_payslips()


@router.get(
    "/{slip_id}",
    response_model=PayslipResponse,
)
def get_payslip(
    slip_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> PayslipResponse:
    service = PayslipService(uow)
    slip = service.get_payslip(slip_id)
    if slip is None:
        raise HTTPException(status_code=404, detail="Payslip not found.")
    return slip


@router.post(
    "",
    response_model=PayslipResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_payslip(
    request: CreatePayslipRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> PayslipResponse:
    service = PayslipService(uow)
    return service.create_payslip(request, user_id=current_user.user_id)


@router.get(
    "/{slip_id}/pdf",
)
def download_payslip_pdf(
    slip_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> Response:
    service = PayslipService(uow)
    pdf_bytes = service.generate_pdf_bytes(slip_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={slip_id}.pdf"
        },
    )
