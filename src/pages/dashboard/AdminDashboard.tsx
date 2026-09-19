import { Users, Database, Activity, DatabaseBackup } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { DashboardCard } from "@/components/common/DashboardCard";
import { Card, CardContent } from "@/components/ui/Card";
import { StatusBadge } from "@/components/common/StatusBadge";
import { appUsers, systemMonitors, backups, auditLogs } from "@/data/mockData";
import { formatDateTime } from "@/utils/format";

export default function AdminDashboard() {
  const dbMonitor = systemMonitors.find((m) => m.component === "MySQL");
  const lastBackup = backups[0];

  return (
    <div>
      <PageHeader title="System Administration" description="Users, infrastructure health and backup status." />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <DashboardCard label="Total Users" value={String(appUsers.length)} icon={<Users className="h-[18px] w-[18px]" />} tone="primary" />
        <DashboardCard label="Database Status" value={dbMonitor?.databaseStatus ?? "\u2014"} icon={<Database className="h-[18px] w-[18px]" />} tone={dbMonitor?.databaseStatus === "Connected" ? "success" : "danger"} />
        <DashboardCard label="API Health" value="Healthy" icon={<Activity className="h-[18px] w-[18px]" />} tone="success" />
        <DashboardCard label="Last Backup" value={lastBackup.status} icon={<DatabaseBackup className="h-[18px] w-[18px]" />} tone={lastBackup.status === "Completed" ? "success" : "danger"} />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardContent>
            <p className="mb-3 text-sm font-semibold text-text">Service Monitoring</p>
            <div className="space-y-2.5">
              {systemMonitors.map((m) => (
                <div key={m.id} className="flex items-center justify-between rounded-lg border border-border px-3 py-2.5">
                  <div>
                    <p className="text-sm font-medium text-text">{m.component}</p>
                    <p className="text-xs text-text-muted">CPU {m.cpuUsage}% \u00b7 Mem {m.memoryUsage}% \u00b7 {m.responseTimeMs}ms</p>
                  </div>
                  <StatusBadge status={m.serviceStatus} />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent>
            <p className="mb-3 text-sm font-semibold text-text">Recent Audit Activity</p>
            <div className="space-y-2.5">
              {auditLogs.slice(0, 6).map((a) => (
                <div key={a.id} className="flex items-center justify-between border-b border-border pb-2.5 last:border-0 last:pb-0">
                  <div>
                    <p className="text-sm font-medium text-text">{a.action}</p>
                    <p className="text-xs text-text-muted">{a.userName} \u00b7 {formatDateTime(a.timestamp)}</p>
                  </div>
                  <StatusBadge status={a.status} />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
