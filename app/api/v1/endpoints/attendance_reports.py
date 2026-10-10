from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies.authorization import require_permission
from app.api.dependencies.unit_of_work import get_unit_of_work
from app.application.common.unit_of_work import UnitOfWork
from app.application.reporting.attendance_report_service import (
    AttendanceReportFilters,
    AttendanceReportService,
    InvalidAttendanceReportCursor,
    InvalidAttendanceReportFilters,
)
from app.application.reporting.schemas import AttendanceReportPage
from app.infrastructure.persistence.models.user import User


router = APIRouter(prefix="/reports", tags=["Attendance Reports"])


@router.get("/attendance", response_model=AttendanceReportPage)
def get_attendance_report(
    current_user: Annotated[
        User, Depends(require_permission("report.attendance.read"))
    ],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    employee_id: Annotated[int | None, Query(gt=0)] = None,
    department_id: Annotated[int | None, Query(gt=0)] = None,
    attendance_status: Annotated[
        Literal["PRESENT", "ABSENT", "HALF_DAY", "ON_LEAVE", "HOLIDAY"] | None,
        Query(),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: Annotated[str | None, Query(max_length=2048)] = None,
) -> AttendanceReportPage:
    try:
        filters = AttendanceReportFilters(
            date_from=date_from,
            date_to=date_to,
            employee_id=employee_id,
            department_id=department_id,
            attendance_status=attendance_status,
        )
        return AttendanceReportService(uow).get_page(limit, filters, cursor)
    except InvalidAttendanceReportFilters as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except InvalidAttendanceReportCursor as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid attendance report cursor.",
        ) from exc
