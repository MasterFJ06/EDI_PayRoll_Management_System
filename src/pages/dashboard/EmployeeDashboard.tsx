import { CalendarCheck, Wallet, FileText, CalendarClock } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { DashboardCard } from "@/components/common/DashboardCard";
import { ChartCard } from "@/components/common/ChartCard";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Card, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/context/AuthContext";
import { attendanceRecords, leaveBalances, leaveRequests, payslips } from "@/data/mockData";
import { formatDate, formatINR, monthLabel } from "@/utils/format";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { Link } from "react-router-dom";

export default function EmployeeDashboard() {
  const { user } = useAuth();
  const empId = user?.employeeId ?? "EMP001";

  const myAttendance = attendanceRecords.filter((a) => a.employeeId === empId);
  const presentDays = myAttendance.filter((a) => a.status === "Present").length;
  const myBalances = leaveBalances.filter((b) => b.employeeId === empId);
  const myLeaves = leaveRequests.filter((l) => l.employeeId === empId).slice(0, 4);
  const myPayslip = payslips.find((p) => p.employeeId === empId);

  const attendanceChart = myAttendance.map((a) => ({
    date: formatDate(a.attendanceDate).slice(0, 6),
    hours: a.workingHours,
  }));

  return (
    <div>
      <PageHeader title={`Welcome back, ${user?.firstName}`} description="Here's what's happening with your attendance, leave and payroll." />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <DashboardCard label="Present Days (This Week)" value={String(presentDays)} icon={<CalendarCheck className="h-[18px] w-[18px]" />} tone="success" />
        <DashboardCard label="Leave Balance (Casual)" value={String(myBalances.find(b => b.leaveType === "Casual")?.balance ?? 0)} icon={<CalendarClock className="h-[18px] w-[18px]" />} tone="info" />
        <DashboardCard label="Latest Net Salary" value={myPayslip ? formatINR(myPayslip.netSalary) : "\u2014"} icon={<Wallet className="h-[18px] w-[18px]" />} tone="primary" />
        <DashboardCard label="Pending Leave Requests" value={String(myLeaves.filter(l => l.status === "Pending").length)} icon={<FileText className="h-[18px] w-[18px]" />} tone="warning" />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <ChartCard title="My Attendance" subtitle="Working hours over recent days">
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={attendanceChart}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#64748B" }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: "#64748B" }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ borderRadius: 8, borderColor: "#E2E8F0", fontSize: 12 }} />
                <Bar dataKey="hours" fill="#2563EB" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        </div>

        <Card>
          <CardContent>
            <p className="mb-3 text-sm font-semibold text-text">Leave Balances</p>
            <div className="space-y-3">
              {myBalances.map((b) => (
                <div key={b.leaveType}>
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-medium text-text">{b.leaveType}</span>
                    <span className="text-text-muted">{b.balance}/{b.entitled} days</span>
                  </div>
                  <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
                    <div className="h-full rounded-full bg-secondary" style={{ width: `${(b.balance / b.entitled) * 100}%` }} />
                  </div>
                </div>
              ))}
            </div>
            <Link to="/leave">
              <Button variant="outline" size="sm" className="mt-4 w-full">Apply for Leave</Button>
            </Link>
          </CardContent>
        </Card>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardContent>
            <div className="mb-3 flex items-center justify-between">
              <p className="text-sm font-semibold text-text">My Leave Requests</p>
              <Link to="/leave" className="text-xs font-medium text-secondary hover:underline">View all</Link>
            </div>
            <div className="space-y-2.5">
              {myLeaves.map((l) => (
                <div key={l.id} className="flex items-center justify-between rounded-lg border border-border px-3 py-2.5">
                  <div>
                    <p className="text-sm font-medium text-text">{l.leaveType} Leave</p>
                    <p className="text-xs text-text-muted">{formatDate(l.startDate)} \u2013 {formatDate(l.endDate)} \u00b7 {l.totalDays} day(s)</p>
                  </div>
                  <StatusBadge status={l.status} />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent>
            <div className="mb-3 flex items-center justify-between">
              <p className="text-sm font-semibold text-text">Latest Payslip</p>
              <Link to="/payroll/payslips" className="text-xs font-medium text-secondary hover:underline">View all</Link>
            </div>
            {myPayslip ? (
              <div className="space-y-2 text-sm">
                <div className="flex justify-between"><span className="text-text-muted">Payroll Month</span><span className="font-medium text-text">{monthLabel(myPayslip.payrollMonth)}</span></div>
                <div className="flex justify-between"><span className="text-text-muted">Gross Salary</span><span className="font-medium text-text">{formatINR(myPayslip.grossSalary)}</span></div>
                <div className="flex justify-between"><span className="text-text-muted">Deductions</span><span className="font-medium text-danger">-{formatINR(myPayslip.deductions)}</span></div>
                <div className="flex justify-between border-t border-border pt-2"><span className="font-medium text-text">Net Salary</span><span className="font-semibold text-success">{formatINR(myPayslip.netSalary)}</span></div>
              </div>
            ) : <p className="text-sm text-text-muted">No payslip available yet.</p>}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
