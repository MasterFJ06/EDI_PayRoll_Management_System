from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.organization import router as organization_router
from app.api.v1.endpoints.employee import router as employee_router
from app.api.v1.endpoints.attendance import router as attendance_router
from app.api.v1.endpoints.leave import router as leave_router
from app.api.v1.endpoints.compensation import router as compensation_router
from app.api.v1.endpoints.payroll import router as payroll_router
from app.api.v1.endpoints.work_calendar import router as work_calendar_router
from app.api.v1.endpoints.overtime_policy import router as overtime_policy_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(organization_router)
api_router.include_router(attendance_router)
api_router.include_router(employee_router)
api_router.include_router(leave_router)
api_router.include_router(compensation_router)
api_router.include_router(payroll_router)
api_router.include_router(work_calendar_router)
api_router.include_router(overtime_policy_router)
