from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status

from app.api.dependencies.authorization import require_permission
from app.api.dependencies.unit_of_work import get_unit_of_work
from app.application.common.unit_of_work import UnitOfWork
from app.application.organization.work_calendar_schemas import (
    WorkCalendarDateOverrideCreateRequest,
    WorkCalendarDateOverrideResponse,
    WorkCalendarVersionCreateRequest,
    WorkCalendarVersionResponse,
)
from app.application.organization.work_calendar_service import WorkCalendarService
from app.infrastructure.persistence.models.user import User


router = APIRouter(prefix="/work-calendar-versions", tags=["Organization Work Calendar"])


@router.post("", response_model=WorkCalendarVersionResponse, status_code=201)
def create_work_calendar_version(
    body: WorkCalendarVersionCreateRequest,
    request: Request,
    current_user: Annotated[User, Depends(require_permission("organization.calendar.manage"))],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> WorkCalendarVersionResponse:
    return WorkCalendarService(uow).create_version(
        body,
        current_user.user_id,
        getattr(request.state, "request_id", None),
    )


@router.get("/{version_id}", response_model=WorkCalendarVersionResponse)
def get_work_calendar_version(
    version_id: Annotated[int, Path(gt=0)],
    current_user: Annotated[User, Depends(require_permission("organization.calendar.read"))],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> WorkCalendarVersionResponse:
    result = WorkCalendarService(uow).get_version(version_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Work Calendar version not found.")
    return result


@router.post(
    "/{version_id}/date-overrides",
    response_model=WorkCalendarDateOverrideResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_work_calendar_date_override(
    version_id: Annotated[int, Path(gt=0)],
    body: WorkCalendarDateOverrideCreateRequest,
    request: Request,
    current_user: Annotated[User, Depends(require_permission("organization.calendar.manage"))],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> WorkCalendarDateOverrideResponse:
    return WorkCalendarService(uow).create_date_override(
        version_id,
        body,
        current_user.user_id,
        getattr(request.state, "request_id", None),
    )
