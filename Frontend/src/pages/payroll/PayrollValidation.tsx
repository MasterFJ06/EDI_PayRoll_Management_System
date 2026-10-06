import { useEffect, useState } from "react";
import { FileCheck2, CheckCircle2, AlertTriangle, XCircle, ShieldAlert, RotateCcw } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { FilterBar } from "@/components/common/FilterBar";
import { SearchBar } from "@/components/common/SearchBar";
import { Select } from "@/components/ui/Select";
import { Button } from "@/components/ui/Button";
import { DashboardCard } from "@/components/common/DashboardCard";
import { StatusBadge } from "@/components/common/StatusBadge";
import { DataTable, type Column } from "@/components/tables/DataTable";
import { ErrorState } from "@/components/common/ErrorState";
import { listValidationIssues, resolveValidationIssue } from "@/services/validationService";
import { employeeName } from "@/data/mockData";
import { formatDateTime } from "@/utils/format";
import type { PayrollValidationIssue } from "@/types";

export default function PayrollValidation() {
  const [items, setItems] = useState<PayrollValidationIssue[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [search, setSearch] = useState("");
  const [severityFilter, setSeverityFilter] = useState("all");

  async function load() {
    setLoading(true); setError(false);
    try { setItems(await listValidationIssues()); } catch { setError(true); } finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []);

  const filtered = items.filter((v) => {
    const matchSearch = employeeName(v.employeeId).toLowerCase().includes(search.toLowerCase()) || v.validationType.toLowerCase().includes(search.toLowerCase());
    const matchSeverity = severityFilter === "all" || v.severity === severityFilter;
    return matchSearch && matchSeverity;
  });

  const passed = items.filter((v) => v.status === "Resolved").length;
  const warnings = items.filter((v) => v.severity === "Warning" && v.status === "Open").length;
  const errors = items.filter((v) => v.severity === "Error" && v.status === "Open").length;
  const critical = items.filter((v) => v.severity === "Critical" && v.status === "Open").length;

  async function handleResolve(v: PayrollValidationIssue) { await resolveValidationIssue(v.id); load(); }

  const columns: Column<PayrollValidationIssue>[] = [
    { key: "employee", header: "Employee", sortValue: (v) => employeeName(v.employeeId), render: (v) => <span className="font-medium text-text">{employeeName(v.employeeId)}</span> },
    { key: "type", header: "Validation Type", render: (v) => v.validationType },
    { key: "message", header: "Message", render: (v) => <span className="text-text-muted max-w-xs block">{v.message}</span> },
    { key: "severity", header: "Severity", render: (v) => (
      <span className={`inline-flex items-center gap-1 text-xs font-semibold ${v.severity === "Critical" || v.severity === "Error" ? "text-danger" : v.severity === "Warning" ? "text-warning" : "text-info"}`}>
        {v.severity}
      </span>
    ) },
    { key: "timestamp", header: "Timestamp", sortValue: (v) => v.timestamp, render: (v) => formatDateTime(v.timestamp) },
    { key: "status", header: "Status", render: (v) => <StatusBadge status={v.status} /> },
    { key: "actions", header: "Actions", render: (v) => (
      v.status === "Open" ? <Button size="sm" variant="outline" onClick={() => handleResolve(v)}><RotateCcw className="h-3.5 w-3.5" /> Resolve</Button> : <span className="text-xs text-text-muted">\u2014</span>
    ) },
  ];

  return (
    <div>
      <PageHeader
        title="Payroll Validation"
        description="Pre-processing checks that surface data issues before payroll is finalized."
        icon={<FileCheck2 className="h-5 w-5" />}
      />

      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <DashboardCard label="Passed" value={String(passed)} icon={<CheckCircle2 className="h-[18px] w-[18px]" />} tone="success" />
        <DashboardCard label="Warnings" value={String(warnings)} icon={<AlertTriangle className="h-[18px] w-[18px]" />} tone="warning" />
        <DashboardCard label="Errors" value={String(errors)} icon={<XCircle className="h-[18px] w-[18px]" />} tone="danger" />
        <DashboardCard label="Critical" value={String(critical)} icon={<ShieldAlert className="h-[18px] w-[18px]" />} tone="danger" />
      </div>

      <FilterBar>
        <SearchBar value={search} onChange={setSearch} placeholder="Search by employee or validation type" className="w-full sm:w-80" />
        <Select value={severityFilter} onChange={(e) => setSeverityFilter(e.target.value)} className="w-full sm:w-44">
          <option value="all">All Severities</option>
          <option>Information</option><option>Warning</option><option>Error</option><option>Critical</option>
        </Select>
      </FilterBar>

      <div className="mt-4">
        {error ? <ErrorState onRetry={load} /> : (
          <DataTable columns={columns} data={filtered} rowKey={(v) => v.id} loading={loading} pageSize={8} emptyTitle="No validation issues found" />
        )}
      </div>
    </div>
  );
}
