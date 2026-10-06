from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.api.dependencies.current_user import get_current_user
from app.application.monitoring.monitoring_service import MonitoringService
from app.infrastructure.persistence.models.user import User

router = APIRouter(
    prefix="/monitoring",
    tags=["System Monitoring"],
)

monitoring_service = MonitoringService()


@router.get(
    "",
)
def get_monitoring_stats(
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[dict[str, Any]]:
    return monitoring_service.get_system_monitors()
