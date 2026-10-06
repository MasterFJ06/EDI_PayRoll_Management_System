import { useEffect, useState } from "react";
import { FileText, Download, Printer, Mail, ShieldHalf } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { FilterBar } from "@/components/common/FilterBar";
import { SearchBar } from "@/components/common/SearchBar";
import { Select } from "@/components/ui/Select";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { StatusBadge } from "@/components/common/StatusBadge";
import { DataTable, type Column } from "@/components/tables/DataTable";
import { ErrorState } from "@/components/common/ErrorState";
import { listPayslips, downloadPayslipPdf } from "@/services/payslipService";
import { employees, employeeName, departmentName, designationName } from "@/data/mockData";
import { formatDate, formatINR, monthLabel } from "@/utils/format";
import { useAuth } from "@/context/AuthContext";
import type { Payslip } from "@/types";

export default function Payslips() {
  const { user, can } = useAuth();
  const [items, setItems] = useState<Payslip[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [search, setSearch] = useState("");
  const [monthFilter, setMonthFilter] = useState("all");
  const [viewing, setViewing] = useState<Payslip | null>(null);

  async function load() {
    setLoading(true); setError(false);
    try { setItems(await listPayslips()); } catch { setError(true); } finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []);

  const scoped = can("payslip.view.all") ? items : items.filter((p) => p.employeeId === user?.employeeId);
  const filtered = scoped.filter((p) => {
    const matchSearch = employeeName(p.employeeId).toLowerCase().includes(search.toLowerCase());
    const matchMonth = monthFilter === "all" || p.payrollMonth === monthFilter;
    return matchSearch && matchMonth;
  });

  const columns: Column<Payslip>[] = [
    { key: "id", header: "Payslip ID", render: (p) => <span className="font-mono text-xs text-text-muted">{p.id}</span> },
    { key: "employee", header: "Employee", sortValue: (p) => employeeName(p.employeeId), render: (p) => <span className="font-medium text-text">{employeeName(p.employeeId)}</span> },
    { key: "month", header: "Payroll Month", sortValue: (p) => p.payrollMonth, render: (p) => monthLabel(p.payrollMonth) },
    { key: "gross", header: "Gross Salary", sortValue: (p) => p.grossSalary, render: (p) => formatINR(p.grossSalary) },
    { key: "net", header: "Net Salary", sortValue: (p) => p.netSalary, render: (p) => <span className="font-semibold text-success">{formatINR(p.netSalary)}</span> },
    { key: "generated", header: "Generated Date", sortValue: (p) => p.generatedDate, render: (p) => formatDate(p.generatedDate) },
    { key: "status", header: "Status", render: (p) => <StatusBadge status={p.status} /> },
    { key: "actions", header: "Actions", render: (p) => (
      <Button variant="outline" size="sm" onClick={() => setViewing(p)}><FileText className="h-3.5 w-3.5" /> View</Button>
    ) },
  ];

  return (
    <div>
      <PageHeader
        title="Payslip Generation"
        description="Generated payslips for each processed payroll month."
        icon={<FileText className="h-5 w-5" />}
      />

      <FilterBar>
        <SearchBar value={search} onChange={setSearch} placeholder="Search by employee" className="w-full sm:w-64" />
        <Select value={monthFilter} onChange={(e) => setMonthFilter(e.target.value)} className="w-full sm:w-48">
          <option value="all">All Months</option>
          <option value="2026-07">{monthLabel("2026-07")}</option>
        </Select>
      </FilterBar>

      <div className="mt-4">
        {error ? <ErrorState onRetry={load} /> : (
          <DataTable columns={columns} data={filtered} rowKey={(p) => p.id} loading={loading} pageSize={8} emptyTitle="No payslips found" />
        )}
      </div>

      <Dialog
        open={!!viewing} onClose={() => setViewing(null)} title="Payslip" size="lg"
        footer={viewing && <>
          <Button variant="outline" onClick={() => window.print()}><Printer className="h-4 w-4" /> Print</Button>
          <Button variant="outline" onClick={() => window.alert(`Email action queued for ${viewing.id}. Connect the FastAPI mail service to send it.`)}><Mail className="h-4 w-4" /> Email</Button>
          <Button onClick={() => downloadPayslipPdf(viewing.id)}><Download className="h-4 w-4" /> Download Payslip</Button>
        </>}
      >
        {viewing && <PayslipDocument payslip={viewing} />}
      </Dialog>
    </div>
  );
}

function PayslipDocument({ payslip }: { payslip: Payslip }) {
  const employee = employees.find((e) => e.id === payslip.employeeId);
  return (
    <div className="rounded-lg border border-border p-5">
      <div className="flex items-center justify-between border-b border-border pb-4">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-white"><ShieldHalf className="h-5 w-5" /></div>
          <div>
            <p className="font-display text-sm font-bold text-text">EPMS Pvt. Ltd.</p>
            <p className="text-[11px] text-text-muted">Hinjawadi Phase 2, Pune, Maharashtra 411057</p>
          </div>
        </div>
        <div className="text-right">
          <p className="text-sm font-semibold text-text">Salary Slip</p>
          <p className="text-xs text-text-muted">{monthLabel(payslip.payrollMonth)}</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 border-b border-border py-4 text-sm">
        <div><span className="text-text-muted">Employee Name: </span><span className="font-medium text-text">{employeeName(payslip.employeeId)}</span></div>
        <div><span className="text-text-muted">Employee Code: </span><span className="font-medium text-text">{employee?.employeeCode}</span></div>
        <div><span className="text-text-muted">Department: </span><span className="text-text">{employee ? departmentName(employee.departmentId) : "\u2014"}</span></div>
        <div><span className="text-text-muted">Designation: </span><span className="text-text">{employee ? designationName(employee.designationId) : "\u2014"}</span></div>
      </div>

      <div className="grid grid-cols-2 gap-6 py-4">
        <div>
          <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-text-muted">Earnings</p>
          <div className="flex justify-between border-b border-border py-1.5 text-sm"><span className="text-text-muted">Basic Salary</span><span className="text-text">{formatINR(payslip.basicSalary)}</span></div>
          <div className="flex justify-between border-b border-border py-1.5 text-sm"><span className="text-text-muted">Allowances</span><span className="text-text">{formatINR(payslip.allowances)}</span></div>
          <div className="flex justify-between py-1.5 text-sm font-medium"><span>Gross Salary</span><span>{formatINR(payslip.grossSalary)}</span></div>
        </div>
        <div>
          <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-text-muted">Deductions</p>
          <div className="flex justify-between border-b border-border py-1.5 text-sm"><span className="text-text-muted">Total Deductions</span><span className="text-danger">-{formatINR(payslip.deductions)}</span></div>
        </div>
      </div>

      <div className="flex items-center justify-between rounded-lg bg-primary-50 px-4 py-3">
        <span className="text-sm font-semibold text-text">Net Salary</span>
        <span className="text-lg font-bold text-primary">{formatINR(payslip.netSalary)}</span>
      </div>

      <div className="mt-4 flex items-center justify-between text-xs text-text-muted">
        <span>Generated on {formatDate(payslip.generatedDate)}</span>
        <span>Authorized: {payslip.digitalSignature}</span>
      </div>
    </div>
  );
}
