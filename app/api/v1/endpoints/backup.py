from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies.current_user import get_current_user
from app.application.backup.backup_service import BackupService
from app.infrastructure.persistence.models.user import User

router = APIRouter(
    prefix="/backups",
    tags=["Backups"],
)

backup_service = BackupService()


@router.get(
    "",
)
def list_backups(
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[dict[str, Any]]:
    return backup_service.list_backups()


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
)
def create_backup(
    payload: dict[str, Any],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    b_type = payload.get("type", "Full")
    created_by = payload.get("createdBy", current_user.username)
    return backup_service.create_backup(b_type, created_by)


@router.post(
    "/{backup_id}/restore",
)
def restore_backup(
    backup_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    res = backup_service.restore_backup(backup_id)
    if res is None:
        raise HTTPException(status_code=404, detail="Backup record not found.")
    return res
