from datetime import date, datetime

from app.domain.shared.entity import Entity
from app.domain.shared.exceptions import BusinessRuleViolation


class Attendance(Entity[int | None]):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    HALF_DAY = "HALF_DAY"
    ON_LEAVE = "ON_LEAVE"
    HOLIDAY = "HOLIDAY"

    VALID_STATUSES = {
        PRESENT,
        ABSENT,
        HALF_DAY,
        ON_LEAVE,
        HOLIDAY,
    }

    def __init__(
        self,
        attendance_id: int | None,
        employee_id: int,
        attendance_date: date,
        attendance_status: str,
        check_in_time: datetime | None = None,
        check_out_time: datetime | None = None,
    ) -> None:
        normalized_status = attendance_status.strip().upper()

        if employee_id <= 0:
            raise BusinessRuleViolation(
                "Employee ID must be positive."
            )

        if normalized_status not in self.VALID_STATUSES:
            raise BusinessRuleViolation(
                "Attendance status must be PRESENT, ABSENT, HALF_DAY, "
                "ON_LEAVE, or HOLIDAY."
            )

        if (
            check_in_time is not None
            and check_out_time is not None
            and check_out_time < check_in_time
        ):
            raise BusinessRuleViolation(
                "Check-out time cannot be earlier than check-in time."
            )

        super().__init__(attendance_id)

        self.employee_id = employee_id
        self.attendance_date = attendance_date
        self.check_in_time = check_in_time
        self.check_out_time = check_out_time
        self.attendance_status = normalized_status