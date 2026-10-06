import { useEffect, useState } from "react";
import { BellRing } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { Card, CardContent } from "@/components/ui/Card";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { EmptyState } from "@/components/common/EmptyState";
import { listLeaveAlerts } from "@/services/reportService";
import { employeeName } from "@/data/mockData";
import { formatDate } from "@/utils/format";
import type { LeaveAlert } from "@/types";

const TONE = {
  Normal: "border-green-200 bg-success-50 text-success",
  Warning: "border-amber-200 bg-warning-50 text-warning",
  Critical: "border-red-200 bg-danger-50 text-danger",
};

export default function LeaveAlerts() {
  const [items, setItems] = useState<LeaveAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  async function load() {
    setLoading(true); setError(false);
    try { setItems(await listLeaveAlerts()); } catch { setError(true); } finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []);

  return (
    <div>
      <PageHeader title="Leave Balance Alerts" description="Employees whose leave balance requires attention." icon={<BellRing className="h-5 w-5" />} />

      {loading && <LoadingState />}
      {error && <ErrorState onRetry={load} />}
      {!loading && !error && items.length === 0 && <EmptyState title="No leave alerts" />}

      {!loading && !error && items.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((a) => (
            <Card key={a.id} className={`border ${TONE[a.alertType]}`}>
              <CardContent>
                <div className="flex items-center justify-between">
                  <p className="font-semibold text-text">{employeeName(a.employeeId)}</p>
                  <span className={`h-2 w-2 rounded-full ${a.alertType === "Critical" ? "bg-danger" : a.alertType === "Warning" ? "bg-warning" : "bg-success"}`} />
                </div>
                <p className="mt-1 text-sm text-text-muted">{a.leaveType} Leave</p>
                <p className="mt-3 text-2xl font-semibold text-text">{a.currentBalance} <span className="text-sm font-normal text-text-muted">/ threshold {a.threshold}</span></p>
                <p className="mt-2 text-xs text-text-muted">{a.message}</p>
                <p className="mt-3 text-[11px] text-text-muted">{formatDate(a.createdDate)}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
