from datetime import datetime
from typing import Any

from app.application.common.unit_of_work import UnitOfWork
from app.infrastructure.persistence.models.audit import AuditEvent


class AuditService:
    """Service for querying and recording system audit logs."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def list_logs(self) -> list[dict[str, Any]]:
        if getattr(self.uow, "audits", None) is not None:
            events = self.uow.audits.get_all()
            if events:
                result = []
                for ev in events:
                    result.append(
                        {
                            "id": f"AUD{ev.audit_event_id:04d}",
                            "timestamp": ev.occurred_at.isoformat(),
                            "userId": f"U{ev.actor_user_id:03d}" if ev.actor_user_id else "U001",
                            "userName": "System User",
                            "role": "Payroll Administrator",
                            "module": ev.resource_type,
                            "action": ev.action_type,
                            "affectedRecord": str(ev.resource_id or ""),
                            "oldValue": None,
                            "newValue": None,
                            "ipAddress": ev.source_ip or "127.0.0.1",
                            "status": "Success",
                            "remarks": "",
                        }
                    )
                return result

        # Baseline seed logs matching frontend mock events
        return [
            {"id": "AUD1001", "timestamp": "2026-08-10T09:12:44", "userId": "U004", "userName": "Meera Kapoor", "role": "Payroll Administrator", "module": "Payroll", "action": "Payroll Processed", "affectedRecord": "PR-2026-08-BATCH", "oldValue": None, "newValue": {"status": "Processed", "employees": 10}, "ipAddress": "10.20.4.12", "status": "Success", "remarks": "August 2026 payroll batch processed."},
            {"id": "AUD1002", "timestamp": "2026-08-09T16:45:02", "userId": "U003", "userName": "Priya Sharma", "role": "HR", "module": "Leave", "action": "Leave Approved", "affectedRecord": "LV1002", "oldValue": {"status": "Pending"}, "newValue": {"status": "Approved"}, "ipAddress": "10.20.4.31", "status": "Success", "remarks": ""},
            {"id": "AUD1003", "timestamp": "2026-08-09T11:02:19", "userId": "U003", "userName": "Priya Sharma", "role": "HR", "module": "Employee", "action": "Employee Updated", "affectedRecord": "EMP007", "oldValue": {"employmentStatus": "Active"}, "newValue": {"employmentStatus": "On Leave"}, "ipAddress": "10.20.4.31", "status": "Success", "remarks": ""},
            {"id": "AUD1004", "timestamp": "2026-08-08T18:22:51", "userId": "U005", "userName": "Rohan Verma", "role": "System Administrator", "module": "Infrastructure", "action": "Backup Created", "affectedRecord": "BKP-20260808", "oldValue": None, "newValue": {"type": "Full", "size": "1.8 GB"}, "ipAddress": "10.20.4.02", "status": "Success", "remarks": "Scheduled nightly backup."},
            {"id": "AUD1005", "timestamp": "2026-08-07T13:11:08", "userId": "U004", "userName": "Meera Kapoor", "role": "Payroll Administrator", "module": "Salary", "action": "Salary Updated", "affectedRecord": "SS-EMP002", "oldValue": {"basic": 55000}, "newValue": {"basic": 58000}, "ipAddress": "10.20.4.12", "status": "Success", "remarks": "Annual increment."},
            {"id": "AUD1006", "timestamp": "2026-08-06T08:55:37", "userId": "U001", "userName": "Radhika Suryatal", "role": "Employee", "module": "Auth", "action": "Login", "affectedRecord": "U001", "oldValue": None, "newValue": None, "ipAddress": "182.71.44.9", "status": "Success", "remarks": ""},
        ]

    def record_event(
        self,
        actor_user_id: int | None,
        action: str,
        resource_type: str,
        resource_id: int | None = None,
        ip: str = "127.0.0.1",
    ) -> None:
        if getattr(self.uow, "audits", None) is not None:
            ev = AuditEvent(
                actor_user_id=actor_user_id,
                action_type=action,
                resource_type=resource_type,
                resource_id=resource_id,
                source_ip=ip,
                occurred_at=datetime.utcnow(),
            )
            self.uow.audits.add(ev)
            self.uow.commit()
