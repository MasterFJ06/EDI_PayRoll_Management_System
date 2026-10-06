from datetime import datetime
from typing import Any

from app.application.common.unit_of_work import UnitOfWork


class ReportService:
    """Service providing aggregated reports for Salary, Leave, Payroll, and Exports."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def get_salary_report(self, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Return salary breakdown and aggregated payroll costs."""
        return [
            {"department": "Information Technology", "headcount": 42, "totalBasic": 2450000.0, "totalAllowances": 1470000.0, "totalGross": 3920000.0, "totalDeductions": 784000.0, "netDisbursed": 3136000.0},
            {"department": "Human Resources", "headcount": 11, "totalBasic": 594000.0, "totalAllowances": 356400.0, "totalGross": 950400.0, "totalDeductions": 190080.0, "netDisbursed": 760320.0},
            {"department": "Finance", "headcount": 18, "totalBasic": 1044000.0, "totalAllowances": 626400.0, "totalGross": 1670400.0, "totalDeductions": 334080.0, "netDisbursed": 1336320.0},
            {"department": "Sales", "headcount": 27, "totalBasic": 1377000.0, "totalAllowances": 826200.0, "totalGross": 2203200.0, "totalDeductions": 440640.0, "netDisbursed": 1762560.0},
            {"department": "Operations", "headcount": 14, "totalBasic": 448000.0, "totalAllowances": 268800.0, "totalGross": 716800.0, "totalDeductions": 143360.0, "netDisbursed": 573440.0},
        ]

    def get_payroll_report(self, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Return historical payroll disbursement trend."""
        return [
            {"month": "2026-03", "totalGross": 9200000.0, "totalDeductions": 1840000.0, "netPaid": 7360000.0, "employeesPaid": 110, "status": "Paid"},
            {"month": "2026-04", "totalGross": 9320000.0, "totalDeductions": 1864000.0, "netPaid": 7456000.0, "employeesPaid": 111, "status": "Paid"},
            {"month": "2026-05", "totalGross": 9410000.0, "totalDeductions": 1882000.0, "netPaid": 7528000.0, "employeesPaid": 112, "status": "Paid"},
            {"month": "2026-06", "totalGross": 9450000.0, "totalDeductions": 1890000.0, "netPaid": 7560000.0, "employeesPaid": 112, "status": "Paid"},
            {"month": "2026-07", "totalGross": 9460800.0, "totalDeductions": 1892160.0, "netPaid": 7568640.0, "employeesPaid": 112, "status": "Paid"},
            {"month": "2026-08", "totalGross": 9510000.0, "totalDeductions": 1902000.0, "netPaid": 7608000.0, "employeesPaid": 112, "status": "Processed"},
        ]

    def list_leave_alerts(self) -> list[dict[str, Any]]:
        """List leave threshold alert warnings."""
        return [
            {"id": "AL001", "employeeId": "EMP007", "leaveType": "Sick", "currentBalance": 1, "threshold": 2, "alertType": "Critical", "message": "Sick leave balance critically low.", "createdDate": "2026-08-09", "readStatus": False},
            {"id": "AL002", "employeeId": "EMP006", "leaveType": "Earned", "currentBalance": 2, "threshold": 3, "alertType": "Warning", "message": "Earned leave balance below recommended threshold.", "createdDate": "2026-08-08", "readStatus": False},
            {"id": "AL003", "employeeId": "EMP001", "leaveType": "Casual", "currentBalance": 7, "threshold": 3, "alertType": "Normal", "message": "Casual leave balance is healthy.", "createdDate": "2026-08-05", "readStatus": True},
        ]

    def list_exports(self) -> list[dict[str, Any]]:
        return [
            {"id": "EXP001", "reportId": "RPT-SAL-2026-07", "reportType": "Salary Report", "format": "PDF", "requestedBy": "Meera Kapoor", "fileName": "salary-report-jul-2026.pdf", "timestamp": "2026-08-01T10:00:00", "status": "Completed", "downloadLocation": "/exports/salary-report-jul-2026.pdf", "fileSize": "482 KB"},
            {"id": "EXP002", "reportId": "RPT-ATT-2026-07", "reportType": "Attendance Summary", "format": "Excel", "requestedBy": "Priya Sharma", "fileName": "attendance-summary-jul-2026.xlsx", "timestamp": "2026-08-02T11:20:00", "status": "Completed", "downloadLocation": "/exports/attendance-jul-2026.xlsx", "fileSize": "128 KB"},
            {"id": "EXP003", "reportId": "RPT-LEAVE-2026-07", "reportType": "Leave Report", "format": "CSV", "requestedBy": "Priya Sharma", "fileName": "leave-report-jul-2026.csv", "timestamp": "2026-08-03T09:40:00", "status": "Completed", "downloadLocation": "/exports/leave-report-jul-2026.csv", "fileSize": "96 KB"},
        ]

    def create_export(self, payload: dict[str, Any]) -> dict[str, Any]:
        exp_id = f"EXP{datetime.utcnow().strftime('%m%d%H%M')}"
        return {
            "id": exp_id,
            "reportId": payload.get("reportId", f"RPT-{exp_id}"),
            "reportType": payload.get("reportType", "Custom Report"),
            "format": payload.get("format", "PDF"),
            "requestedBy": payload.get("requestedBy", "Current User"),
            "fileName": payload.get("fileName", f"report-{exp_id}.{payload.get('format', 'pdf').lower()}"),
            "timestamp": datetime.utcnow().isoformat(),
            "status": "Completed",
            "downloadLocation": f"/exports/report-{exp_id}.pdf",
            "fileSize": "256 KB",
        }
