import { Users, Wallet, TrendingUp, CalendarClock } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { DashboardCard } from "@/components/common/DashboardCard";
import { ChartCard } from "@/components/common/ChartCard";
import { employees, departments, payrollRecords } from "@/data/mockData";
import { formatINR } from "@/utils/format";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend, AreaChart, Area, XAxis, YAxis, CartesianGrid } from "recharts";

const COLORS = ["#1E3A8A", "#2563EB", "#0284C7", "#16A34A", "#D97706"];

export default function ManagementDashboard() {
  const augustNet = payrollRecords.filter((p) => p.payrollMonth === "2026-08").reduce((s, p) => s + p.netSalary, 0);
  const deptChart = departments.map((d) => ({ name: d.name, value: d.employeeCount }));

  const attendanceTrend = [
    { month: "Mar", rate: 94 }, { month: "Apr", rate: 95 }, { month: "May", rate: 93 },
    { month: "Jun", rate: 96 }, { month: "Jul", rate: 95 }, { month: "Aug", rate: 97 },
  ];

  return (
    <div>
      <PageHeader title="Management Overview" description="Workforce, payroll and organizational trends at a glance." />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <DashboardCard label="Total Workforce" value={String(employees.length)} icon={<Users className="h-[18px] w-[18px]" />} tone="primary" trend={{ value: "+4.2%", direction: "up" }} />
        <DashboardCard label="August Net Payroll" value={formatINR(augustNet)} icon={<Wallet className="h-[18px] w-[18px]" />} tone="info" />
        <DashboardCard label="Avg. Attendance Rate" value="95.6%" icon={<TrendingUp className="h-[18px] w-[18px]" />} tone="success" trend={{ value: "+1.1%", direction: "up" }} />
        <DashboardCard label="Open Leave Requests" value="3" icon={<CalendarClock className="h-[18px] w-[18px]" />} tone="warning" />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <ChartCard title="Department Distribution" subtitle="Share of total headcount">
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie data={deptChart} dataKey="value" nameKey="name" innerRadius={55} outerRadius={90} paddingAngle={3}>
                {deptChart.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip contentStyle={{ borderRadius: 8, borderColor: "#E2E8F0", fontSize: 12 }} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Attendance Trend" subtitle="Organization-wide attendance rate (%)">
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={attendanceTrend}>
              <defs>
                <linearGradient id="attendanceFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#2563EB" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#2563EB" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
              <XAxis dataKey="month" tick={{ fontSize: 11, fill: "#64748B" }} axisLine={false} tickLine={false} />
              <YAxis domain={[85, 100]} tick={{ fontSize: 11, fill: "#64748B" }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ borderRadius: 8, borderColor: "#E2E8F0", fontSize: 12 }} />
              <Area type="monotone" dataKey="rate" stroke="#2563EB" fill="url(#attendanceFill)" strokeWidth={2.5} />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
    </div>
  );
}
