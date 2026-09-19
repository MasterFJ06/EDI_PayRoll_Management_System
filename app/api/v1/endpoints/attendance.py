from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies.current_user import get_current_user
from app.api.dependencies.unit_of_work import get_unit_of_work
from app.application.attendance.attendance_service import AttendanceService
from app.application.attendance.schemas import (
    AttendanceCreateRequest,
    AttendanceResponse,
)
from app.application.common.unit_of_work import UnitOfWork
from app.infrastructure.persistence.models.user import User


router = APIRouter(prefix="", tags=["Attendance"])


@router.post(
    "/attendance",
    response_model=AttendanceResponse,
    status_code=201,
)
def create_attendance(
    request: AttendanceCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> AttendanceResponse:
    service = AttendanceService(uow)
    return service.create(request)