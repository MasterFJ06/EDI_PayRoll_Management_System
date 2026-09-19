import { useEffect, useState } from "react";
import { ActivitySquare, Cpu, MemoryStick, Database, Timer } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { Card, CardContent } from "@/components/ui/Card";
import { DashboardCard } from "@/components/common/DashboardCard";
import { StatusBadge } from "@/components/common/StatusBadge";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { listSystemMonitors } from "@/services/systemService";
import { formatDateTime } from "@/utils/format";
import type { SystemMonitor } from "@/types";

export default function Monitoring() {
  const [items, setItems] = useState<SystemMonitor[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  async function load() {
    setLoading(true); setError(false);
    try { setItems(await listSystemMonitors()); } catch { setError(true); } finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []);

  if (loading) return <LoadingState label="Loading system status..." />;
  if (error) return <ErrorState onRetry={load} />;

  const avgCpu = Math.round(items.reduce((s, m) => s + m.cpuUsage, 0) / items.length);
  const avgMem = Math.round(items.reduce((s, m) => s + m.memoryUsage, 0) / items.length);
  const avgResponse = Math.round(items.reduce((s, m) => s + m.responseTimeMs, 0) / items.length);
  const healthyCount = items.filter((m) => m.healthStatus === "Healthy").length;

  return (
    <div>
      <PageHeader title="System Monitoring" description="Live-style health of every backend service component." icon={<ActivitySquare className="h-5 w-5" />} />

      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <DashboardCard label="Avg. CPU Usage" value={`${avgCpu}%`} icon={<Cpu className="h-[18px] w-[18px]" />} tone="primary" />
        <DashboardCard label="Avg. Memory Usage" value={`${avgMem}%`} icon={<MemoryStick className="h-[18px] w-[18px]" />} tone="info" />
        <DashboardCard label="Avg. Response Time" value={`${avgResponse}ms`} icon={<Timer className="h-[18px] w-[18px]" />} tone="success" />
        <DashboardCard label="Healthy Services" value={`${healthyCount}/${items.length}`} icon={<Database className="h-[18px] w-[18px]" />} tone={healthyCount === items.length ? "success" : "warning"} />
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((m) => (
          <Card key={m.id}>
            <CardContent>
              <div className="flex items-center justify-between">
                <p className="font-semibold text-text">{m.component}</p>
                <StatusBadge status={m.serviceStatus} />
              </div>

              <div className="mt-4 space-y-3">
                <UsageBar label="CPU Usage" value={m.cpuUsage} />
                <UsageBar label="Memory Usage" value={m.memoryUsage} />
              </div>

              <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
                <div className="rounded-lg bg-slate-50 px-2.5 py-2">
                  <p className="text-text-muted">Database</p>
                  <p className="mt-0.5 font-medium text-text">{m.databaseStatus}</p>
                </div>
                <div className="rounded-lg bg-slate-50 px-2.5 py-2">
                  <p className="text-text-muted">Response Time</p>
                  <p className="mt-0.5 font-medium text-text">{m.responseTimeMs}ms</p>
                </div>
              </div>

              <div className="mt-3 flex items-center justify-between text-[11px] text-text-muted">
                <span>Health: <span className={m.healthStatus === "Healthy" ? "text-success font-medium" : "text-warning font-medium"}>{m.healthStatus}</span></span>
                <span>{formatDateTime(m.timestamp)}</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

function UsageBar({ label, value }: { label: string; value: number }) {
  const color = value > 70 ? "bg-danger" : value > 50 ? "bg-warning" : "bg-success";
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-xs">
        <span className="text-text-muted">{label}</span>
        <span className="font-medium text-text">{value}%</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}
