from abc import ABC, abstractmethod
from datetime import date, datetime

from app.domain.leave.leave_balance import LeaveBalance
from app.domain.leave.leave_request import LeaveRequest
from app.domain.leave.leave_request_day import LeaveRequestDay
from app.domain.leave.leave_type import LeaveType


class LeaveTypeRepository(ABC):
    @abstractmethod
    def get_by_id(self, leave_type_id: int) -> LeaveType | None: ...

    @abstractmethod
    def get_by_code(self, leave_type_code: str) -> LeaveType | None: ...

    @abstractmethod
    def get_by_name(self, leave_type_name: str) -> LeaveType | None: ...

    @abstractmethod
    def add(self, leave_type: LeaveType) -> LeaveType: ...


class LeaveBalanceRepository(ABC):
    @abstractmethod
    def get_by_id(self, leave_balance_id: int) -> LeaveBalance | None: ...

    @abstractmethod
    def get_by_employee_type_year(
        self, employee_id: int, leave_type_id: int, balance_year: int
    ) -> LeaveBalance | None: ...

    @abstractmethod
    def add(self, leave_balance: LeaveBalance) -> LeaveBalance: ...


class LeaveRequestRepository(ABC):
    @abstractmethod
    def get_by_id(self, leave_request_id: int) -> LeaveRequest | None: ...

    @abstractmethod
    def add(self, leave_request: LeaveRequest) -> LeaveRequest: ...

    @abstractmethod
    def get_days(self, leave_request_id: int) -> list[LeaveRequestDay]: ...

    @abstractmethod
    def get_approved_allocations_for_employee_period(
        self, employee_id: int, start_date: date, end_date: date
    ) -> list[tuple[LeaveRequest, LeaveRequestDay, LeaveType | None]]: ...

    @abstractmethod
    def add_days(self, leave_request_id: int, days: list[LeaveRequestDay]) -> None: ...

    @abstractmethod
    def find_approved_conflicts(
        self, employee_id: int, leave_dates: list[date], excluding_request_id: int
    ) -> list[date]: ...

    @abstractmethod
    def transition_status(
        self,
        leave_request_id: int,
        expected_status: str,
        target_status: str,
        reviewed_by_employee_id: int | None = None,
        reviewed_at: datetime | None = None,
        review_comment: str | None = None,
    ) -> bool: ...
