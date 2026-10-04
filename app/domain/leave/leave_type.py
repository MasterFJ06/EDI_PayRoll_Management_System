from app.domain.shared.entity import Entity
from app.domain.shared.exceptions import BusinessRuleViolation


class LeaveType(Entity[int | None]):
    def __init__(
        self,
        leave_type_id: int | None,
        leave_type_code: str,
        leave_type_name: str,
        description: str | None = None,
        is_active: bool = True,
    ) -> None:
        code = leave_type_code.strip()
        name = leave_type_name.strip()
        if not code:
            raise BusinessRuleViolation("Leave type code cannot be blank.")
        if len(code) > 30:
            raise BusinessRuleViolation("Leave type code cannot exceed 30 characters.")
        if not name:
            raise BusinessRuleViolation("Leave type name cannot be blank.")
        if len(name) > 100:
            raise BusinessRuleViolation("Leave type name cannot exceed 100 characters.")
        normalized_description = description.strip() if description is not None else None
        if normalized_description is not None and len(normalized_description) > 500:
            raise BusinessRuleViolation("Leave type description cannot exceed 500 characters.")
        super().__init__(leave_type_id)
        self.leave_type_code = code
        self.leave_type_name = name
        self.description = normalized_description
        self.is_active = is_active
