import { useEffect, useState } from "react";
import {
  PlayCircle, Users, ListChecks, CalendarCheck, CalendarClock, Wallet, Receipt, Percent,
  TrendingUp, TrendingDown, ShieldCheck, Cog, ThumbsUp, FileText, BarChart3, Check,
} from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { Card, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import { StatusBadge } from "@/components/common/StatusBadge";
import { DataTable, type Column } from "@/components/tables/DataTable";
import { ErrorState } from "@/components/common/ErrorState";
import { listPayroll, processPayrollMonth, approvePayroll } from "@/services/payrollService";
import { employeeName } from "@/data/mockData";
import { formatINR, monthLabel } from "@/utils/format";
import { useAuth } from "@/context/AuthContext";
import type { PayrollRecord } from "@/types";

const STEPS = [
  { label: "Select Payroll Month", icon: CalendarClock },
  { label: "Load Employees", icon: Users },
  { label: "Load Attendance", icon: CalendarCheck },
  { label: "Load Leave", icon: ListChecks },
  { label: "Load Salary Structures", icon: Wallet },
  { label: "Calculate Earnings", icon: TrendingUp },
  { label: "Calculate Deductions", icon: TrendingDown },
  { label: "Calculate Gross Salary", icon: Receipt },
  { label: "Calculate Net Salary", icon: Percent },
  { label: "Validate Payroll", icon: ShieldCheck },
  { label: "Process Payroll", icon: Cog },
  { label: "Approve Payroll", icon: ThumbsUp },
  { label: "Generate Payslips", icon: FileText },
  { label: "Generate Reports", icon: BarChart3 },
];

export default function PayrollProcessing() {
  const { can } = useAuth();
  const [items, setItems] = useState<PayrollRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [month, setMonth] = useState("2026-08");
  const [processing, setProcessing] = useState(false);
  const [activeStep, setActiveStep] = useState(1);

  async function load() {
    setLoading(true); setError(false);
    try { setItems(await listPayroll()); } catch { setError(true); } finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []);

  const monthRecords = items.filter((p) => p.payrollMonth === month);
  const statusOf = monthRecords[0]?.status ?? "Draft";
  const stepIndex = { Draft: 4, Validated: 9, Processed: 10, Approved: 11, Paid: 13 }[statusOf] ?? 1;

  async function handleProcess() {
    setProcessing(true);
    setActiveStep(5);
    await new Promise((r) => setTimeout(r, 500));
    setActiveStep(9);
    await processPayrollMonth(month);
    setActiveStep(13);
    setProcessing(false);
    load();
  }

  async function handleApproveAll() {
    for (const p of monthRecords) await approvePayroll(p.id);
    load();
  }

  const columns: Column<PayrollRecord>[] = [
    { key: "employee", header: "Employee", sortValue: (p) => employeeName(p.employeeId), render: (p) => <span className="font-medium text-text">{employeeName(p.employeeId)}</span> },
    { key: "basic", header: "Basic Salary", sortValue: (p) => p.basicSalary, render: (p) => formatINR(p.basicSalary) },
    { key: "allowances", header: "Allowances", sortValue: (p) => p.allowances, render: (p) => formatINR(p.allowances) },
    { key: "overtime", header: "Overtime", sortValue: (p) => p.overtime, render: (p) => formatINR(p.overtime) },
    { key: "tax", header: "Tax", sortValue: (p) => p.tax, render: (p) => formatINR(p.tax) },
    { key: "gross", header: "Gross Salary", sortValue: (p) => p.grossSalary, render: (p) => <span className="font-medium text-text">{formatINR(p.grossSalary)}</span> },
    { key: "net", header: "Net Salary", sortValue: (p) => p.netSalary, render: (p) => <span className="font-semibold text-success">{formatINR(p.netSalary)}</span> },
    { key: "status", header: "Status", render: (p) => <StatusBadge status={p.status} /> },
  ];

  return (
    <div>
      <PageHeader
        title="Payroll Processing"
        description="Run the end-to-end payroll workflow for a selected month."
        icon={<PlayCircle className="h-5 w-5" />}
        actions={
          <div className="flex items-center gap-2">
            <Select value={month} onChange={(e) => setMonth(e.target.value)} className="w-44">
              <option value="2026-08">{monthLabel("2026-08")}</option>
              <option value="2026-07">{monthLabel("2026-07")}</option>
            </Select>
            {can("payroll.process") && (
              <Button onClick={handleProcess} loading={processing}>Process Payroll</Button>
            )}
            {can("payroll.approve") && statusOf === "Processed" && (
              <Button variant="success" onClick={handleApproveAll}>Approve All</Button>
            )}
          </div>
        }
      />

      <Card className="mb-6">
        <CardContent>
          <p className="mb-4 text-sm font-semibold text-text">Payroll Workflow \u2014 {monthLabel(month)}</p>
          <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4 lg:grid-cols-7">
            {STEPS.map((step, i) => {
              const done = i <= stepIndex && !processing;
              const current = processing && i === activeStep;
              return (
                <div key={step.label} className={`flex flex-col items-center gap-1.5 rounded-lg border p-2.5 text-center transition-colors ${done ? "border-primary-100 bg-primary-50" : current ? "border-secondary bg-secondary-50 animate-pulse" : "border-border bg-slate-50/50"}`}>
                  <div className={`flex h-8 w-8 items-center justify-center rounded-full ${done ? "bg-primary text-white" : current ? "bg-secondary text-white" : "bg-slate-200 text-slate-500"}`}>
                    {done ? <Check className="h-4 w-4" /> : <step.icon className="h-4 w-4" />}
                  </div>
                  <p className={`text-[10.5px] font-medium leading-tight ${done ? "text-primary" : "text-text-muted"}`}>{step.label}</p>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      <div className="mb-4 flex items-center gap-2">
        <span className="text-sm text-text-muted">Batch status:</span>
        <StatusBadge status={statusOf} />
        <span className="text-sm text-text-muted">\u00b7 {monthRecords.length} employees</span>
      </div>

      {error ? <ErrorState onRetry={load} /> : (
        <DataTable columns={columns} data={monthRecords} rowKey={(p) => p.id} loading={loading} pageSize={8} emptyTitle="No payroll records for this month" />
      )}
    </div>
  );
}
