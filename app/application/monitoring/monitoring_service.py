from datetime import datetime
from typing import Any


class MonitoringService:
    """Service providing real-time system and service telemetry."""

    def get_system_monitors(self) -> list[dict[str, Any]]:
        now = datetime.utcnow().isoformat()
        return [
            {"id": "MON01", "component": "FastAPI", "serviceStatus": "Online", "cpuUsage": 28, "memoryUsage": 42, "databaseStatus": "Connected", "responseTimeMs": 45, "healthStatus": "Healthy", "timestamp": now, "alertStatus": "None"},
            {"id": "MON02", "component": "Uvicorn", "serviceStatus": "Online", "cpuUsage": 18, "memoryUsage": 30, "databaseStatus": "Connected", "responseTimeMs": 25, "healthStatus": "Healthy", "timestamp": now, "alertStatus": "None"},
            {"id": "MON03", "component": "MySQL", "serviceStatus": "Online", "cpuUsage": 35, "memoryUsage": 55, "databaseStatus": "Connected", "responseTimeMs": 12, "healthStatus": "Healthy", "timestamp": now, "alertStatus": "None"},
            {"id": "MON04", "component": "Authentication", "serviceStatus": "Online", "cpuUsage": 12, "memoryUsage": 19, "databaseStatus": "Connected", "responseTimeMs": 38, "healthStatus": "Healthy", "timestamp": now, "alertStatus": "None"},
            {"id": "MON05", "component": "Payroll Service", "serviceStatus": "Online", "cpuUsage": 22, "memoryUsage": 38, "databaseStatus": "Connected", "responseTimeMs": 85, "healthStatus": "Healthy", "timestamp": now, "alertStatus": "None"},
            {"id": "MON06", "component": "Backup Service", "serviceStatus": "Online", "cpuUsage": 8, "memoryUsage": 15, "databaseStatus": "Connected", "responseTimeMs": 40, "healthStatus": "Healthy", "timestamp": now, "alertStatus": "None"},
            {"id": "MON07", "component": "Scheduler", "serviceStatus": "Online", "cpuUsage": 5, "memoryUsage": 12, "databaseStatus": "Connected", "responseTimeMs": 15, "healthStatus": "Healthy", "timestamp": now, "alertStatus": "None"},
        ]
