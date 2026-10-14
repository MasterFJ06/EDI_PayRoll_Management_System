from datetime import date

from sqlalchemy import func, select, text, update
from sqlalchemy.orm import Session

from app.domain.payroll.repository import PayrollRunRepository as PayrollRunRepositoryContract
from app.core.config import get_settings
from app.infrastructure.persistence.models.payroll_run import PayrollRunModel


class PayrollRunRepository(PayrollRunRepositoryContract):
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, payroll_run_id: int) -> PayrollRunModel | None:
        return self.session.scalar(
            select(PayrollRunModel).where(PayrollRunModel.payroll_run_id == payroll_run_id)
        )

    def get_by_period(self, payroll_year: int, payroll_month: int) -> PayrollRunModel | None:
        return self.session.scalar(
            select(PayrollRunModel).where(
                PayrollRunModel.payroll_year == payroll_year,
                PayrollRunModel.payroll_month == payroll_month,
            )
        )

    def get_statuses_overlapping_dates(
        self, start_date: date, end_date: date | None
    ) -> list[str]:
        period_index = (
            PayrollRunModel.payroll_year * 12 + PayrollRunModel.payroll_month - 1
        )
        start_index = start_date.year * 12 + start_date.month - 1
        statement = select(PayrollRunModel.status).where(period_index >= start_index)
        if end_date is not None:
            end_index = end_date.year * 12 + end_date.month - 1
            statement = statement.where(period_index <= end_index)
        return list(self.session.scalars(statement))

    def add(self, payroll_run: PayrollRunModel) -> PayrollRunModel:
        self.session.add(payroll_run)
        self.session.flush()
        return payroll_run

    def claim_for_processing(self, payroll_run_id: int) -> int | None:
        dialect_name = self.session.get_bind().dialect.name
        if dialect_name not in {"mysql", "sqlite"}:
            raise RuntimeError(
                f"Payroll attempt claims do not support database dialect {dialect_name}."
            )

        locked_run = None
        if dialect_name == "mysql":
            locked_run = self.session.scalar(
                select(PayrollRunModel)
                .where(PayrollRunModel.payroll_run_id == payroll_run_id)
                .with_for_update()
            )
            if locked_run is None or locked_run.status != "CREATED":
                return None

        lease_seconds = get_settings().payroll_attempt_lease_seconds
        result = self.session.execute(
            update(PayrollRunModel)
            .where(
                PayrollRunModel.payroll_run_id == payroll_run_id,
                PayrollRunModel.status == "CREATED",
            )
            .values(
                status="PROCESSING",
                attempt_number=PayrollRunModel.attempt_number + 1,
                started_at=self._database_current_time(dialect_name),
                attempt_lease_expires_at=self._lease_expiration(
                    dialect_name, lease_seconds
                ),
            )
            .execution_options(synchronize_session="fetch")
        )
        if result.rowcount != 1:
            return None

        if locked_run is not None:
            self.session.expire(locked_run)
        return self.session.scalar(
            select(PayrollRunModel.attempt_number).where(
                PayrollRunModel.payroll_run_id == payroll_run_id
            )
        )

    def lock_active_attempt(
        self, payroll_run_id: int, attempt_number: int
    ) -> PayrollRunModel | None:
        dialect_name = self.session.get_bind().dialect.name
        statement = (
            select(PayrollRunModel)
            .where(
                PayrollRunModel.payroll_run_id == payroll_run_id,
                PayrollRunModel.status == "PROCESSING",
                PayrollRunModel.attempt_number == attempt_number,
                PayrollRunModel.attempt_lease_expires_at
                > self._database_current_time(dialect_name),
            )
            .with_for_update()
        )
        return self.session.scalar(statement)

    def renew_active_attempt_lease(
        self, payroll_run_id: int, attempt_number: int
    ) -> bool:
        """Extend only a still-live lease for the current PROCESSING attempt."""
        dialect_name = self.session.get_bind().dialect.name
        lease_seconds = get_settings().payroll_attempt_lease_seconds
        result = self.session.execute(
            update(PayrollRunModel)
            .where(
                PayrollRunModel.payroll_run_id == payroll_run_id,
                PayrollRunModel.status == "PROCESSING",
                PayrollRunModel.attempt_number == attempt_number,
                PayrollRunModel.attempt_lease_expires_at
                > self._database_current_time(dialect_name),
            )
            .values(
                attempt_lease_expires_at=self._lease_expiration(
                    dialect_name, lease_seconds
                )
            )
            .execution_options(synchronize_session="fetch")
        )
        return result.rowcount == 1

    def lock_expired_processing_attempt(
        self, payroll_run_id: int
    ) -> PayrollRunModel | None:
        """Lock an expired PROCESSING row using database time as authority."""
        dialect_name = self.session.get_bind().dialect.name
        return self.session.scalar(
            select(PayrollRunModel)
            .where(
                PayrollRunModel.payroll_run_id == payroll_run_id,
                PayrollRunModel.status == "PROCESSING",
                PayrollRunModel.attempt_lease_expires_at.is_not(None),
                PayrollRunModel.attempt_lease_expires_at
                <= self._database_current_time(dialect_name),
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    def recover_expired_attempt(
        self, payroll_run_id: int, attempt_number: int
    ) -> bool:
        """Conditionally fail the same expired attempt while its row is locked."""
        dialect_name = self.session.get_bind().dialect.name
        result = self.session.execute(
            update(PayrollRunModel)
            .where(
                PayrollRunModel.payroll_run_id == payroll_run_id,
                PayrollRunModel.status == "PROCESSING",
                PayrollRunModel.attempt_number == attempt_number,
                PayrollRunModel.attempt_lease_expires_at.is_not(None),
                PayrollRunModel.attempt_lease_expires_at
                <= self._database_current_time(dialect_name),
            )
            .values(
                status="FAILED",
                attempt_lease_expires_at=None,
            )
            .execution_options(synchronize_session="fetch")
        )
        return result.rowcount == 1

    def lock_failed_attempt(self, payroll_run_id: int) -> PayrollRunModel | None:
        return self.session.scalar(
            select(PayrollRunModel)
            .where(PayrollRunModel.payroll_run_id == payroll_run_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    def lock_for_finalization(self, payroll_run_id: int) -> PayrollRunModel | None:
        return self.session.scalar(
            select(PayrollRunModel)
            .where(PayrollRunModel.payroll_run_id == payroll_run_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    def finalize_processed_run(self, payroll_run_id: int) -> bool:
        dialect_name = self.session.get_bind().dialect.name
        if dialect_name not in {"mysql", "sqlite"}:
            raise RuntimeError(
                f"Payroll Run finalization does not support database dialect {dialect_name}."
            )
        result = self.session.execute(
            update(PayrollRunModel)
            .where(
                PayrollRunModel.payroll_run_id == payroll_run_id,
                PayrollRunModel.status == "PROCESSED",
            )
            .values(
                status="FINALIZED",
                finalized_at=self._database_current_time(dialect_name),
            )
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:
            return False
        run = self.session.get(PayrollRunModel, payroll_run_id)
        if run is not None:
            self.session.refresh(run)
        return True

    def retry_failed_attempt(
        self, payroll_run_id: int, expected_attempt_number: int
    ) -> int | None:
        dialect_name = self.session.get_bind().dialect.name
        lease_seconds = get_settings().payroll_attempt_lease_seconds
        result = self.session.execute(
            update(PayrollRunModel)
            .where(
                PayrollRunModel.payroll_run_id == payroll_run_id,
                PayrollRunModel.status == "FAILED",
                PayrollRunModel.attempt_number == expected_attempt_number,
            )
            .values(
                status="PROCESSING",
                attempt_number=PayrollRunModel.attempt_number + 1,
                started_at=self._database_current_time(dialect_name),
                attempt_lease_expires_at=self._lease_expiration(
                    dialect_name, lease_seconds
                ),
            )
            .execution_options(synchronize_session="fetch")
        )
        if result.rowcount != 1:
            return None
        return expected_attempt_number + 1

    def mark_failed_if_processing(
        self, payroll_run_id: int, attempt_number: int
    ) -> bool:
        run = self.lock_active_attempt(payroll_run_id, attempt_number)
        if run is None:
            return False
        run.status = "FAILED"
        run.attempt_lease_expires_at = None
        self.session.flush()
        return True

    def mark_processed_if_processing(
        self, payroll_run_id: int, attempt_number: int
    ) -> bool:
        run = self.lock_active_attempt(payroll_run_id, attempt_number)
        if run is None:
            return False
        dialect_name = self.session.get_bind().dialect.name
        run.status = "PROCESSED"
        run.completed_at = self._database_current_time(dialect_name)
        run.attempt_lease_expires_at = None
        self.session.flush()
        return True

    @staticmethod
    def _database_current_time(dialect_name: str):
        if dialect_name == "mysql":
            return func.current_timestamp(6)
        if dialect_name == "sqlite":
            return func.current_timestamp()
        raise RuntimeError(
            f"Payroll attempt leases do not support database dialect {dialect_name}."
        )

    @classmethod
    def _lease_expiration(cls, dialect_name: str, lease_seconds: int):
        database_now = cls._database_current_time(dialect_name)
        if dialect_name == "mysql":
            return func.timestampadd(text("SECOND"), lease_seconds, database_now)
        if dialect_name == "sqlite":
            return func.datetime(database_now, f"+{lease_seconds} seconds")
        raise RuntimeError(
            f"Payroll attempt leases do not support database dialect {dialect_name}."
        )
