import { Users, UserCheck, UserPlus, CalendarClock } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { DashboardCard } from "@/components/common/DashboardCard";
import { ChartCard } from "@/components/common/ChartCard";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Card, CardContent } from "@/components/ui/Card";
import { employees, departments, leaveRequests, employeeName } from "@/data/mockData";
import { formatDate } from "@/utils/format";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

export default function HRDashboard() {
  const active = employees.filter((e) => e.employmentStatus === "Active").length;
  const newHires = employees.filter((e) => e.joiningDate >= "2023-01-01").length;
  const pendingLeave = leaveRequests.filter((l) => l.status === "Pending").length;

  const deptChart = departments.map((d) => ({ name: d.code, count: d.employeeCount }));
  const statusBreakdown = ["Active", "On Leave", "Suspended", "Terminated"].map((s) => ({
    status: s, count: employees.filter((e) => e.employmentStatus === s).length,
  }));

  return (
    <div>
      <PageHeader title="HR Overview" description="Workforce composition, hiring and leave activity across the organization." />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <DashboardCard label="Total Employees" value={String(employees.length)} icon={<Users className="h-[18px] w-[18px]" />} tone="primary" trend={{ value: "+4.2%", direction: "up" }} />
        <DashboardCard label="Active Employees" value={String(active)} icon={<UserCheck className="h-[18px] w-[18px]" />} tone="success" />
        <DashboardCard label="New Employees (Since 2023)" value={String(newHires)} icon={<UserPlus className="h-[18px] w-[18px]" />} tone="info" />
        <DashboardCard label="Pending Leave Requests" value={String(pendingLeave)} icon={<CalendarClock className="h-[18px] w-[18px]" />} tone="warning" />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <ChartCard title="Department Distribution" subtitle="Headcount by department">
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={deptChart}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#64748B" }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: "#64748B" }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ borderRadius: 8, borderColor: "#E2E8F0", fontSize: 12 }} />
                <Bar dataKey="count" fill="#1E3A8A" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        </div>

        <Card>
          <CardContent>
            <p className="mb-3 text-sm font-semibold text-text">Employee Status</p>
            <div className="space-y-3">
              {statusBreakdown.map((s) => (
                <div key={s.status} className="flex items-center justify-between">
                  <StatusBadge status={s.status} />
                  <span className="text-sm font-semibold text-text">{s.count}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="mt-6">
        <Card>
          <CardContent>
            <p className="mb-3 text-sm font-semibold text-text">Recent Leave Requests</p>
            <div className="space-y-2.5">
              {leaveRequests.slice(0, 5).map((l) => (
                <div key={l.id} className="flex items-center justify-between rounded-lg border border-border px-3 py-2.5">
                  <div>
                    <p className="text-sm font-medium text-text">{employeeName(l.employeeId)} \u2014 {l.leaveType}</p>
                    <p className="text-xs text-text-muted">{formatDate(l.startDate)} \u2013 {formatDate(l.endDate)} \u00b7 Applied {formatDate(l.appliedDate)}</p>
                  </div>
                  <StatusBadge status={l.status} />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
