import { Users, CalendarCheck, CalendarClock, ClipboardCheck } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { DashboardCard } from "@/components/common/DashboardCard";
import { ChartCard } from "@/components/common/ChartCard";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Card, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { EmployeeAvatar } from "@/components/common/EmployeeAvatar";
import { employees, attendanceRecords, leaveRequests, employeeName } from "@/data/mockData";
import { formatDate } from "@/utils/format";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { Link } from "react-router-dom";

const team = employees.filter((e) => e.managerId === "EMP004");
const teamIds = new Set(team.map((e) => e.id));

export default function ManagerDashboard() {
  const teamAttendanceToday = attendanceRecords.filter((a) => teamIds.has(a.employeeId) && a.attendanceDate === "2026-08-11");
  const pending = leaveRequests.filter((l) => teamIds.has(l.employeeId) && l.status === "Pending");

  const statusCounts = ["Present", "Absent", "Late", "Half-Day"].map((s) => ({
    name: s, value: teamAttendanceToday.filter((a) => a.status === s).length,
  })).filter((d) => d.value > 0);
  const COLORS = ["#16A34A", "#DC2626", "#D97706", "#0284C7"];

  return (
    <div>
      <PageHeader title="Team Overview" description="Track your team's attendance, leave and approvals." />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <DashboardCard label="Team Size" value={String(team.length)} icon={<Users className="h-[18px] w-[18px]" />} tone="primary" />
        <DashboardCard label="Present Today" value={String(teamAttendanceToday.filter(a => a.status === "Present").length)} icon={<CalendarCheck className="h-[18px] w-[18px]" />} tone="success" />
        <DashboardCard label="On Leave" value={String(team.filter(e => e.employmentStatus === "On Leave").length)} icon={<CalendarClock className="h-[18px] w-[18px]" />} tone="warning" />
        <DashboardCard label="Pending Approvals" value={String(pending.length)} icon={<ClipboardCheck className="h-[18px] w-[18px]" />} tone="danger" />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Card>
            <CardContent>
              <div className="mb-3 flex items-center justify-between">
                <p className="text-sm font-semibold text-text">Pending Leave Approvals</p>
                <Link to="/leave" className="text-xs font-medium text-secondary hover:underline">Go to Leave</Link>
              </div>
              <div className="space-y-2.5">
                {pending.length === 0 && <p className="text-sm text-text-muted py-6 text-center">No pending approvals. You're all caught up.</p>}
                {pending.map((l) => {
                  const emp = employees.find((e) => e.id === l.employeeId);
                  return (
                    <div key={l.id} className="flex items-center justify-between rounded-lg border border-border px-3 py-2.5">
                      <div className="flex items-center gap-2.5">
                        <EmployeeAvatar firstName={emp?.firstName ?? ""} lastName={emp?.lastName ?? ""} size="sm" />
                        <div>
                          <p className="text-sm font-medium text-text">{employeeName(l.employeeId)}</p>
                          <p className="text-xs text-text-muted">{l.leaveType} \u00b7 {formatDate(l.startDate)} \u2013 {formatDate(l.endDate)}</p>
                        </div>
                      </div>
                      <Button size="sm" variant="outline">Review</Button>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </div>

        <ChartCard title="Today's Attendance Mix" subtitle="Team status breakdown">
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={statusCounts} dataKey="value" nameKey="name" innerRadius={50} outerRadius={80} paddingAngle={3}>
                {statusCounts.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip contentStyle={{ borderRadius: 8, borderColor: "#E2E8F0", fontSize: 12 }} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <div className="mt-6">
        <Card>
          <CardContent>
            <p className="mb-3 text-sm font-semibold text-text">My Team</p>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {team.map((e) => (
                <div key={e.id} className="flex items-center gap-3 rounded-lg border border-border p-3">
                  <EmployeeAvatar firstName={e.firstName} lastName={e.lastName} />
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-text">{e.firstName} {e.lastName}</p>
                    <p className="truncate text-xs text-text-muted">{e.employeeCode}</p>
                  </div>
                  <StatusBadge status={e.employmentStatus} />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
