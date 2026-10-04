from abc import ABC, abstractmethod

from app.domain.leave.leave_balance import LeaveBalance
from app.domain.leave.leave_request import LeaveRequest
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
