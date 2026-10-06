from datetime import datetime
from typing import Any


class BackupService:
    """Service managing database backup snapshots and restores."""

    # In-memory store for backups with persistent initial history
    _backups: list[dict[str, Any]] = [
        {"id": "BKP-20260810", "type": "Incremental", "timestamp": "2026-08-10T02:00:00", "size": "312 MB", "location": "s3://epms-backups/2026-08-10-inc.tar.gz", "createdBy": "Scheduler", "status": "Completed", "restoreStatus": "N/A", "checksum": "a1f9c3b8", "remarks": "Automated nightly job."},
        {"id": "BKP-20260808", "type": "Full", "timestamp": "2026-08-08T02:00:00", "size": "1.8 GB", "location": "s3://epms-backups/2026-08-08-full.tar.gz", "createdBy": "Rohan Verma", "status": "Completed", "restoreStatus": "N/A", "checksum": "88bd21ee", "remarks": "Weekly full backup."},
        {"id": "BKP-20260803", "type": "Differential", "timestamp": "2026-08-03T02:00:00", "size": "540 MB", "location": "s3://epms-backups/2026-08-03-diff.tar.gz", "createdBy": "Scheduler", "status": "Completed", "restoreStatus": "Restored", "checksum": "5e02af11", "remarks": "Restored to staging for QA on Aug 9."},
        {"id": "BKP-20260801", "type": "Full", "timestamp": "2026-08-01T02:00:00", "size": "1.7 GB", "location": "s3://epms-backups/2026-08-01-full.tar.gz", "createdBy": "Rohan Verma", "status": "Failed", "restoreStatus": "N/A", "checksum": "—", "remarks": "Disk quota exceeded; retried successfully on Aug 3."},
    ]

    def list_backups(self) -> list[dict[str, Any]]:
        return self._backups

    def create_backup(self, b_type: str = "Full", created_by: str = "System Administrator") -> dict[str, Any]:
        size_str = "1.8 GB" if b_type == "Full" else ("320 MB" if b_type == "Incremental" else "550 MB")
        bkp_id = f"BKP-{datetime.utcnow().strftime('%Y%m%d%H%M')}"
        new_backup = {
            "id": bkp_id,
            "type": b_type,
            "timestamp": datetime.utcnow().isoformat(),
            "size": size_str,
            "location": f"s3://epms-backups/{bkp_id.lower()}.tar.gz",
            "createdBy": created_by,
            "status": "Completed",
            "restoreStatus": "N/A",
            "checksum": f"{abs(hash(bkp_id)):x}"[:8],
            "remarks": "Manually triggered backup snapshot.",
        }
        self._backups.insert(0, new_backup)
        return new_backup

    def restore_backup(self, backup_id: str) -> dict[str, Any] | None:
        for b in self._backups:
            if b["id"] == backup_id:
                b["restoreStatus"] = "Restored"
                return b
        return None
