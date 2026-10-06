from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies.current_user import get_current_user
from app.api.dependencies.unit_of_work import get_unit_of_work
from app.application.attendance.attendance_service import AttendanceService
from app.application.attendance.schemas import (
    AttendanceCreateRequest,
    AttendanceResponse,
    AttendanceUpdateRequest,
)
from app.application.common.unit_of_work import UnitOfWork
from app.infrastructure.persistence.models.user import User

router = APIRouter(prefix="", tags=["Attendance"])


@router.get(
    "/attendance",
    response_model=list[AttendanceResponse],
)
def list_attendance(
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    employee_id: str | None = Query(None, alias="employee_id"),
) -> list[AttendanceResponse]:
    service = AttendanceService(uow)
    return service.list_all(employee_id)


@router.get(
    "/attendance/{attendance_id}",
    response_model=AttendanceResponse,
)
def get_attendance(
    attendance_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> AttendanceResponse:
    service = AttendanceService(uow)
    record = service.get_by_id(attendance_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Attendance record not found.")
    return record


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


@router.put(
    "/attendance/{attendance_id}",
    response_model=AttendanceResponse,
)
def update_attendance(
    attendance_id: str,
    request: AttendanceUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> AttendanceResponse:
    service = AttendanceService(uow)
    updated = service.update(attendance_id, request)
    if updated is None:
        raise HTTPException(status_code=404, detail="Attendance record not found.")
    return updated