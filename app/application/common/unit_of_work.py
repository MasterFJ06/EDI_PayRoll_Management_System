from abc import ABC, abstractmethod
from datetime import datetime
from types import TracebackType
from typing import Self


class UnitOfWork(ABC):
    """Application-level transaction boundary abstraction."""

    users: object
    authorization: object
    audit_events: object
    refresh_tokens: object
    departments: object
    designations: object
    employees: object
    attendance: object
    leave_types: object
    leave_balances: object
    leave_requests: object
    salary_structures: object
    salary_components: object
    salary_revisions: object
    salary_revision_components: object
    employee_salary_assignments: object
    payroll_runs: object
    payroll_run_workforce_snapshots: object
    payroll_results: object
    payroll_result_components: object
    payroll_processing_issues: object
    payslips: object
    work_calendars: object
    overtime_policies: object

    @abstractmethod
    def __enter__(self) -> Self:
        raise NotImplementedError

    @abstractmethod
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def commit(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def rollback(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def begin_workforce_consistent_read(self) -> datetime:
        """Begin Decision 31's explicit MySQL consistent-read transaction."""
        raise NotImplementedError
