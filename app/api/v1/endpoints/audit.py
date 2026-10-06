from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.api.dependencies.current_user import get_current_user
from app.api.dependencies.unit_of_work import get_unit_of_work
from app.application.audit.audit_service import AuditService
from app.application.common.unit_of_work import UnitOfWork
from app.infrastructure.persistence.models.user import User

router = APIRouter(
    prefix="/audit-logs",
    tags=["Audit Logs"],
)


@router.get(
    "",
)
def list_audit_logs(
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> list[dict[str, Any]]:
    service = AuditService(uow)
    return service.list_logs()
