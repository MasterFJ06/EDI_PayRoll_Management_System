from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal

from app.domain.payroll.payroll_processing_issue import PayrollProcessingIssue
from app.domain.payroll.payroll_result import PayrollResult
from app.domain.payroll.payroll_result_report import PayrollResultReportRecord
from app.domain.payroll.payroll_result_component import PayrollResultComponent
from app.domain.payroll.payroll_run import PayrollRun
from app.domain.payroll.payroll_run_workforce_snapshot import (
    PayrollRunWorkforceSnapshot,
)
from app.domain.payroll.payslip import Payslip


class PayrollRunRepository(ABC):
    @abstractmethod
    def get_by_id(self, payroll_run_id: int) -> PayrollRun | None: ...

    @abstractmethod
    def get_by_period(self, payroll_year: int, payroll_month: int) -> PayrollRun | None: ...

    @abstractmethod
    def get_statuses_overlapping_dates(
        self, start_date: date, end_date: date | None
    ) -> list[str]: ...

    @abstractmethod
    def add(self, payroll_run: PayrollRun) -> PayrollRun: ...

    @abstractmethod
    def claim_for_processing(self, payroll_run_id: int) -> int | None: ...

    @abstractmethod
    def lock_active_attempt(
        self, payroll_run_id: int, attempt_number: int
    ) -> PayrollRun | None: ...

    @abstractmethod
    def lock_failed_attempt(
        self, payroll_run_id: int
    ) -> PayrollRun | None: ...

    @abstractmethod
    def lock_for_finalization(self, payroll_run_id: int) -> PayrollRun | None: ...

    @abstractmethod
    def finalize_processed_run(self, payroll_run_id: int) -> bool: ...

    @abstractmethod
    def retry_failed_attempt(
        self, payroll_run_id: int, expected_attempt_number: int
    ) -> int | None: ...

    @abstractmethod
    def mark_failed_if_processing(
        self, payroll_run_id: int, attempt_number: int
    ) -> bool: ...

    @abstractmethod
    def mark_processed_if_processing(
        self, payroll_run_id: int, attempt_number: int
    ) -> bool: ...


class PayrollRunWorkforceSnapshotRepository(ABC):
    @abstractmethod
    def add(
        self,
        snapshot: PayrollRunWorkforceSnapshot,
        expected_attempt_number: int,
    ) -> PayrollRunWorkforceSnapshot: ...

    @abstractmethod
    def get_by_run_and_employee(
        self, payroll_run_id: int, employee_id: int
    ) -> PayrollRunWorkforceSnapshot | None: ...

    @abstractmethod
    def list_by_run_and_attempt(
        self, payroll_run_id: int, attempt_number: int
    ) -> tuple[PayrollRunWorkforceSnapshot, ...]: ...

    @abstractmethod
    def delete_by_run_and_attempt(
        self, payroll_run_id: int, attempt_number: int
    ) -> int: ...


class PayrollResultRepository(ABC):
    @abstractmethod
    def get_by_id(self, payroll_result_id: int) -> PayrollResult | None: ...

    @abstractmethod
    def get_by_id_for_update(
        self, payroll_result_id: int
    ) -> PayrollResult | None: ...

    @abstractmethod
    def get_by_run_and_employee(
        self, payroll_run_id: int, employee_id: int
    ) -> PayrollResult | None: ...

    @abstractmethod
    def list_by_run(self, payroll_run_id: int) -> list[PayrollResult]: ...

    @abstractmethod
    def list_report_page(
        self,
        payroll_run_id: int,
        after_employee_id: int | None,
        after_payroll_result_id: int | None,
        limit: int,
    ) -> list[PayrollResultReportRecord]: ...

    @abstractmethod
    def aggregate_by_run(
        self, payroll_run_id: int
    ) -> tuple[int, Decimal | None, Decimal | None, Decimal | None]: ...

    @abstractmethod
    def add(self, payroll_result: PayrollResult) -> PayrollResult: ...

    @abstractmethod
    def delete_by_run(self, payroll_run_id: int) -> int: ...


class PayrollResultComponentRepository(ABC):
    @abstractmethod
    def get_by_result_and_component(
        self, payroll_result_id: int, salary_component_id: int
    ) -> PayrollResultComponent | None: ...

    @abstractmethod
    def list_by_run(self, payroll_run_id: int) -> list[PayrollResultComponent]: ...

    @abstractmethod
    def add(self, component: PayrollResultComponent) -> PayrollResultComponent: ...

    @abstractmethod
    def delete_by_run(self, payroll_run_id: int) -> int: ...


class PayrollProcessingIssueRepository(ABC):
    @abstractmethod
    def get_by_id(self, payroll_issue_id: int) -> PayrollProcessingIssue | None: ...

    @abstractmethod
    def list_by_run(self, payroll_run_id: int) -> list[PayrollProcessingIssue]: ...

    @abstractmethod
    def has_open_for_update(self, payroll_run_id: int) -> bool: ...

    @abstractmethod
    def add(self, issue: PayrollProcessingIssue) -> PayrollProcessingIssue: ...


class PayslipRepository(ABC):
    @abstractmethod
    def get_by_id(self, payslip_id: int) -> Payslip | None: ...

    @abstractmethod
    def get_by_result_id(self, payroll_result_id: int) -> Payslip | None: ...

    @abstractmethod
    def get_by_number(self, payslip_number: str) -> Payslip | None: ...

    @abstractmethod
    def get_by_run_id(self, payroll_run_id: int) -> Payslip | None: ...

    @abstractmethod
    def get_by_run_id_for_update(self, payroll_run_id: int) -> Payslip | None: ...

    @abstractmethod
    def add(self, payslip: Payslip) -> Payslip: ...
