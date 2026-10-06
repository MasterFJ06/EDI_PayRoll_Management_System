from fastapi import APIRouter

from app.api.v1.endpoints.attendance import router as attendance_router
from app.api.v1.endpoints.audit import router as audit_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.backup import router as backup_router
from app.api.v1.endpoints.deductions import router as deductions_router
from app.api.v1.endpoints.employee import router as employee_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.leave import router as leave_router
from app.api.v1.endpoints.monitoring import router as monitoring_router
from app.api.v1.endpoints.organization import router as organization_router
from app.api.v1.endpoints.payroll import router as payroll_router
from app.api.v1.endpoints.payslip import router as payslip_router
from app.api.v1.endpoints.reports import router as reports_router
from app.api.v1.endpoints.roles import router as roles_router
from app.api.v1.endpoints.salary import router as salary_router
from app.api.v1.endpoints.users import router as users_router
from app.api.v1.endpoints.validation import router as validation_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(roles_router)
api_router.include_router(organization_router)
api_router.include_router(employee_router)
api_router.include_router(attendance_router)
api_router.include_router(leave_router)
api_router.include_router(salary_router)
api_router.include_router(payroll_router)
api_router.include_router(payslip_router)
api_router.include_router(deductions_router)
api_router.include_router(validation_router)
api_router.include_router(reports_router)
api_router.include_router(audit_router)
api_router.include_router(backup_router)
api_router.include_router(monitoring_router)