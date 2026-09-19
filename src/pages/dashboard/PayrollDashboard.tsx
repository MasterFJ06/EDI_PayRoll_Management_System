import { Users, Wallet, TrendingDown, AlertTriangle } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { DashboardCard } from "@/components/common/DashboardCard";
import { ChartCard } from "@/components/common/ChartCard";
import { Card, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { payrollRecords, payrollValidationIssues } from "@/data/mockData";
import { formatINR } from "@/utils/format";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { Link } from "react-router-dom";

export default function PayrollDashboard() {
  const augustRecords = payrollRecords.filter((p) => p.payrollMonth === "2026-08");
  const grossPayroll = augustRecords.reduce((s, p) => s + p.grossSalary, 0);
  const totalDeductions = augustRecords.reduce((s, p) => s + p.totalDeductions, 0);
  const netPayroll = augustRecords.reduce((s, p) => s + p.netSalary, 0);
  const openIssues = payrollValidationIssues.filter((v) => v.status === "Open");

  const trend = [
    { month: "Mar", net: 4.9 }, { month: "Apr", net: 5.1 }, { month: "May", net: 5.0 },
    { month: "Jun", net: 5.3 }, { month: "Jul", net: 5.2 }, { month: "Aug", net: netPayroll / 100000 },
  ];

  return (
    <div>
      <PageHeader
        title="Payroll Overview"
        description="August 2026 payroll status, validation issues and processing progress."
        actions={<Link to="/payroll/processing"><Button>Go to Payroll Processing</Button></Link>}
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <DashboardCard label="Payroll Employees" value={String(augustRecords.length)} icon={<Users className="h-[18px] w-[18px]" />} tone="primary" />
        <DashboardCard label="Gross Payroll" value={formatINR(grossPayroll)} icon={<Wallet className="h-[18px] w-[18px]" />} tone="info" />
        <DashboardCard label="Total Deductions" value={formatINR(totalDeductions)} icon={<TrendingDown className="h-[18px] w-[18px]" />} tone="warning" />
        <DashboardCard label="Validation Issues" value={String(openIssues.length)} icon={<AlertTriangle className="h-[18px] w-[18px]" />} tone="danger" />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <ChartCard title="Monthly Net Payroll Trend" subtitle="In \u20b9 Lakhs">
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
                <XAxis dataKey="month" tick={{ fontSize: 11, fill: "#64748B" }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: "#64748B" }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ borderRadius: 8, borderColor: "#E2E8F0", fontSize: 12 }} />
                <Line type="monotone" dataKey="net" stroke="#2563EB" strokeWidth={2.5} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </ChartCard>
        </div>

        <Card>
          <CardContent>
            <p className="mb-3 text-sm font-semibold text-text">Payroll Status</p>
            <div className="space-y-3">
              {["Draft", "Validated", "Processed", "Approved", "Paid"].map((status) => {
                const count = payrollRecords.filter((p) => p.status === status && p.payrollMonth === "2026-08").length;
                return (
                  <div key={status} className="flex items-center justify-between text-sm">
                    <span className="text-text-muted">{status}</span>
                    <span className="font-semibold text-text">{count}</span>
                  </div>
                );
              })}
            </div>
            <div className="mt-4 h-2 w-full overflow-hidden rounded-full bg-slate-100">
              <div className="h-full bg-primary" style={{ width: "20%" }} />
            </div>
            <p className="mt-1.5 text-xs text-text-muted">August payroll: Draft stage \u2014 2 of 14 steps complete</p>
          </CardContent>
        </Card>
      </div>

      <div className="mt-6">
        <Card>
          <CardContent>
            <div className="mb-3 flex items-center justify-between">
              <p className="text-sm font-semibold text-text">Open Validation Issues</p>
              <Link to="/payroll/validation" className="text-xs font-medium text-secondary hover:underline">View all</Link>
            </div>
            <div className="space-y-2.5">
              {openIssues.map((v) => (
                <div key={v.id} className="flex items-center justify-between rounded-lg border border-border px-3 py-2.5">
                  <div>
                    <p className="text-sm font-medium text-text">{v.validationType} \u2014 {v.employeeId}</p>
                    <p className="text-xs text-text-muted">{v.message}</p>
                  </div>
                  <span className={`text-xs font-semibold ${v.severity === "Critical" ? "text-danger" : v.severity === "Error" ? "text-danger" : "text-warning"}`}>
                    {v.severity}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
