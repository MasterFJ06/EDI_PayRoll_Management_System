from collections.abc import Mapping

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.domain.payroll.payroll_run_workforce_snapshot import (
    PayrollRunWorkforceSnapshot,
)
from app.domain.payroll.repository import (
    PayrollRunWorkforceSnapshotRepository as PayrollRunWorkforceSnapshotRepositoryContract,
)
from app.domain.shared.exceptions import BusinessRuleViolation
from app.infrastructure.persistence.models.payroll_run_workforce_snapshot import (
    PayrollRunWorkforceSnapshotModel,
)
from app.infrastructure.persistence.repositories.payroll_run_repository import (
    PayrollRunRepository,
)


class PayrollRunWorkforceSnapshotRepository(
    PayrollRunWorkforceSnapshotRepositoryContract
):
    def __init__(
        self, session: Session, payroll_runs: PayrollRunRepository | None = None
    ) -> None:
        self.session = session
        self.payroll_runs = payroll_runs or PayrollRunRepository(session)

    def add(
        self,
        snapshot: PayrollRunWorkforceSnapshot,
        expected_attempt_number: int,
    ) -> PayrollRunWorkforceSnapshot:
        if (
            self.payroll_runs.lock_active_attempt(
                snapshot.payroll_run_id, expected_attempt_number
            )
            is None
        ):
            raise BusinessRuleViolation(
                "Payroll processing attempt is no longer active."
            )
        if snapshot.attempt_number != expected_attempt_number:
            raise BusinessRuleViolation(
                "Workforce snapshot attempt does not match the active attempt."
            )
        model = PayrollRunWorkforceSnapshotModel(
            payroll_run_id=snapshot.payroll_run_id,
            employee_id=snapshot.employee_id,
            attempt_number=snapshot.attempt_number,
            snapshot_at=snapshot.snapshot_at,
            snapshot=_json_compatible(snapshot.snapshot),
        )
        self.session.add(model)
        self.session.flush()
        return self._to_entity(model)

    def get_by_run_and_employee(
        self, payroll_run_id: int, employee_id: int
    ) -> PayrollRunWorkforceSnapshot | None:
        model = self.session.get(
            PayrollRunWorkforceSnapshotModel, (payroll_run_id, employee_id)
        )
        return self._to_entity(model) if model is not None else None

    def list_by_run_and_attempt(
        self, payroll_run_id: int, attempt_number: int
    ) -> tuple[PayrollRunWorkforceSnapshot, ...]:
        statement = (
            select(PayrollRunWorkforceSnapshotModel)
            .where(
                PayrollRunWorkforceSnapshotModel.payroll_run_id == payroll_run_id,
                PayrollRunWorkforceSnapshotModel.attempt_number == attempt_number,
            )
            .order_by(PayrollRunWorkforceSnapshotModel.employee_id)
        )
        return tuple(self._to_entity(model) for model in self.session.scalars(statement))

    def delete_by_run_and_attempt(
        self, payroll_run_id: int, attempt_number: int
    ) -> int:
        result = self.session.execute(
            delete(PayrollRunWorkforceSnapshotModel).where(
                PayrollRunWorkforceSnapshotModel.payroll_run_id == payroll_run_id,
                PayrollRunWorkforceSnapshotModel.attempt_number == attempt_number,
            )
        )
        return result.rowcount or 0

    @staticmethod
    def _to_entity(
        model: PayrollRunWorkforceSnapshotModel,
    ) -> PayrollRunWorkforceSnapshot:
        return PayrollRunWorkforceSnapshot(
            payroll_run_id=model.payroll_run_id,
            employee_id=model.employee_id,
            attempt_number=model.attempt_number,
            snapshot_at=model.snapshot_at,
            snapshot=model.snapshot,
        )


def _json_compatible(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _json_compatible(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_compatible(item) for item in value]
    return value
