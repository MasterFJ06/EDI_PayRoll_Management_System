from app.domain.organization.department import Department
from app.domain.organization.designation import Designation
from app.domain.organization.repository import (
    DepartmentRepository,
    DesignationRepository,
)

__all__ = [
    "Department",
    "Designation",
    "DepartmentRepository",
    "DesignationRepository",
]