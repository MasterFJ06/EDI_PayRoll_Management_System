from abc import ABC, abstractmethod

from app.domain.payroll.payroll_processing_issue import PayrollProcessingIssue
from app.domain.payroll.payroll_result import PayrollResult
from app.domain.payroll.payroll_result_component import PayrollResultComponent
from app.domain.payroll.payroll_run import PayrollRun
from app.domain.payroll.payslip import Payslip


class PayrollRunRepository(ABC):
    @abstractmethod
    def get_by_id(self, payroll_run_id: int) -> PayrollRun | None: ...

    @abstractmethod
    def get_by_period(self, payroll_year: int, payroll_month: int) -> PayrollRun | None: ...

    @abstractmethod
    def add(self, payroll_run: PayrollRun) -> PayrollRun: ...


class PayrollResultRepository(ABC):
    @abstractmethod
    def get_by_id(self, payroll_result_id: int) -> PayrollResult | None: ...

    @abstractmethod
    def get_by_run_and_employee(
        self, payroll_run_id: int, employee_id: int
    ) -> PayrollResult | None: ...

    @abstractmethod
    def add(self, payroll_result: PayrollResult) -> PayrollResult: ...


class PayrollResultComponentRepository(ABC):
    @abstractmethod
    def get_by_result_and_component(
        self, payroll_result_id: int, salary_component_id: int
    ) -> PayrollResultComponent | None: ...

    @abstractmethod
    def add(self, component: PayrollResultComponent) -> PayrollResultComponent: ...


class PayrollProcessingIssueRepository(ABC):
    @abstractmethod
    def get_by_id(self, payroll_issue_id: int) -> PayrollProcessingIssue | None: ...

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
    def add(self, payslip: Payslip) -> Payslip: ...
