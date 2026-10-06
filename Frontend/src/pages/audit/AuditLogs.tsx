import { useEffect, useState, type ReactNode } from "react";
import { ScrollText, Eye } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { FilterBar } from "@/components/common/FilterBar";
import { SearchBar } from "@/components/common/SearchBar";
import { Select } from "@/components/ui/Select";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { StatusBadge } from "@/components/common/StatusBadge";
import { DataTable, type Column } from "@/components/tables/DataTable";
import { ErrorState } from "@/components/common/ErrorState";
import { listAuditLogs } from "@/services/auditService";
import { formatDateTime } from "@/utils/format";
import type { AuditLog } from "@/types";

const MODULES = ["Payroll", "Leave", "Employee", "Infrastructure", "Salary", "Auth", "Reports"];

export default function AuditLogs() {
  const [items, setItems] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [search, setSearch] = useState("");
  const [moduleFilter, setModuleFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [viewing, setViewing] = useState<AuditLog | null>(null);

  async function load() {
    setLoading(true); setError(false);
    try { setItems(await listAuditLogs()); } catch { setError(true); } finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []);

  const filtered = items.filter((a) => {
    const matchSearch = `${a.userName} ${a.action} ${a.affectedRecord}`.toLowerCase().includes(search.toLowerCase());
    const matchModule = moduleFilter === "all" || a.module === moduleFilter;
    const matchStatus = statusFilter === "all" || a.status === statusFilter;
    return matchSearch && matchModule && matchStatus;
  });

  const columns: Column<AuditLog>[] = [
    { key: "timestamp", header: "Timestamp", sortValue: (a) => a.timestamp, render: (a) => formatDateTime(a.timestamp) },
    { key: "user", header: "User", sortValue: (a) => a.userName, render: (a) => (
      <div><p className="font-medium text-text">{a.userName}</p><p className="text-xs text-text-muted">{a.role}</p></div>
    ) },
    { key: "module", header: "Module", render: (a) => a.module },
    { key: "action", header: "Action", render: (a) => a.action },
    { key: "record", header: "Affected Record", render: (a) => <span className="font-mono text-xs text-text-muted">{a.affectedRecord}</span> },
    { key: "status", header: "Status", render: (a) => <StatusBadge status={a.status} /> },
    { key: "actions", header: "", render: (a) => <Button variant="ghost" size="icon" onClick={() => setViewing(a)} aria-label="View details"><Eye className="h-4 w-4" /></Button> },
  ];

  return (
    <div>
      <PageHeader title="Audit Logs" description="Traceability of every significant action performed in the system." icon={<ScrollText className="h-5 w-5" />} />

      <FilterBar>
        <SearchBar value={search} onChange={setSearch} placeholder="Search by user, action or record" className="w-full sm:w-72" />
        <Select value={moduleFilter} onChange={(e) => setModuleFilter(e.target.value)} className="w-full sm:w-44">
          <option value="all">All Modules</option>
          {MODULES.map((m) => <option key={m} value={m}>{m}</option>)}
        </Select>
        <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="w-full sm:w-40">
          <option value="all">All Status</option>
          <option>Success</option><option>Failed</option>
        </Select>
      </FilterBar>

      <div className="mt-4">
        {error ? <ErrorState onRetry={load} /> : (
          <DataTable columns={columns} data={filtered} rowKey={(a) => a.id} loading={loading} pageSize={8} emptyTitle="No audit records found" />
        )}
      </div>

      <Dialog open={!!viewing} onClose={() => setViewing(null)} title="Audit Detail" size="md">
        {viewing && (
          <div className="space-y-3 text-sm">
            <DetailRow label="WHO" value={`${viewing.userName} (${viewing.role})`} />
            <DetailRow label="WHAT" value={viewing.action} />
            <DetailRow label="WHEN" value={formatDateTime(viewing.timestamp)} />
            <DetailRow label="MODULE" value={viewing.module} />
            <DetailRow label="RECORD" value={viewing.affectedRecord} />
            <DetailRow label="IP ADDRESS" value={viewing.ipAddress} />
            <DetailRow label="STATUS" value={<StatusBadge status={viewing.status} />} />
            {viewing.remarks && <DetailRow label="REMARKS" value={viewing.remarks} />}
            <div className="grid grid-cols-2 gap-3 pt-2">
              <div>
                <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-text-muted">Old Value</p>
                <pre className="rounded-lg bg-slate-50 p-3 text-[11px] text-text-muted overflow-x-auto">{viewing.oldValue ? JSON.stringify(viewing.oldValue, null, 2) : "null"}</pre>
              </div>
              <div>
                <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-text-muted">New Value</p>
                <pre className="rounded-lg bg-slate-50 p-3 text-[11px] text-text-muted overflow-x-auto">{viewing.newValue ? JSON.stringify(viewing.newValue, null, 2) : "null"}</pre>
              </div>
            </div>
          </div>
        )}
      </Dialog>
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex items-center justify-between border-b border-border pb-2">
      <span className="text-xs font-semibold uppercase tracking-wide text-text-muted">{label}</span>
      <span className="text-text">{value}</span>
    </div>
  );
}
