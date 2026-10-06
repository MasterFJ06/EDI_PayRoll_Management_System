from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies.current_user import get_current_user
from app.api.dependencies.unit_of_work import get_unit_of_work
from app.application.common.unit_of_work import UnitOfWork
from app.application.payroll.report_service import ReportService
from app.infrastructure.persistence.models.user import User

router = APIRouter(
    prefix="",
    tags=["Reports & Exports"],
)


@router.get(
    "/reports/salary",
)
def get_salary_report(
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> Any:
    service = ReportService(uow)
    return service.get_salary_report()


@router.get(
    "/reports/payroll",
)
def get_payroll_report(
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> Any:
    service = ReportService(uow)
    return service.get_payroll_report()


@router.get(
    "/reports/leave",
)
def get_leave_alerts(
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> Any:
    service = ReportService(uow)
    return service.list_leave_alerts()


@router.get(
    "/exports",
)
def list_exports(
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> Any:
    service = ReportService(uow)
    return service.list_exports()


@router.post(
    "/exports",
    status_code=status.HTTP_201_CREATED,
)
def create_export(
    payload: dict[str, Any],
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> Any:
    service = ReportService(uow)
    payload["requestedBy"] = current_user.username
    return service.create_export(payload)
