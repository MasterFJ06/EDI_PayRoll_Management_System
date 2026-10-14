import { ArrowUpRight, CalendarDays, CircleDollarSign, FileText, UsersRound } from "lucide-react";
import { Link } from "react-router-dom";

const reports = [
  { title: "Employee report", description: "Browse persisted employee records with the supported employee filters and cursor pagination.", path: "/employees", icon: UsersRound, endpoint: "GET /api/v1/reports/employees" },
  { title: "Attendance report", description: "Review persisted attendance facts, timestamps, and current employee labels.", path: "/attendance", icon: CalendarDays, endpoint: "GET /api/v1/reports/attendance" },
  { title: "Leave allocations", description: "Review persisted daily leave allocations and request status.", path: "/leave/requests", icon: CalendarDays, endpoint: "GET /api/v1/reports/leave/allocations" },
  { title: "Leave balances", description: "View stored leave balance values without recalculating remaining days.", path: "/leave/balances", icon: FileText, endpoint: "GET /api/v1/reports/leave/balances" },
  { title: "Payroll reports", description: "Retrieve a run to view its summary, employee results, and component breakdown after finalization.", path: "/payroll", icon: CircleDollarSign, endpoint: "GET /api/v1/reports/payroll/runs/{run_id} · /results · /components" },
];

export function ReportsPage() {
  return <div className="space-y-6">
    <section><p className="text-xs font-medium text-slate-400">Insights</p><h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900">Reports</h2><p className="mt-1 text-sm text-slate-500">Open a report backed by persisted EPMS data. The API enforces access for each report.</p></section>
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{reports.map(({ title, description, path, icon: Icon, endpoint }) => <Link key={title} to={path} className="group rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-blue-200 hover:shadow-md focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-blue-600/20">
      <div className="flex items-start justify-between"><div className="grid size-10 place-items-center rounded-lg bg-blue-50 text-blue-700"><Icon size={18} /></div><ArrowUpRight size={17} className="text-slate-300 transition group-hover:text-blue-700" /></div>
      <h3 className="mt-4 text-sm font-semibold text-slate-900">{title}</h3><p className="mt-1 min-h-10 text-xs leading-5 text-slate-500">{description}</p><p className="mt-3 break-all font-mono text-[10px] text-slate-400">{endpoint}</p>
    </Link>)}</div>
    <div className="rounded-lg border border-blue-100 bg-blue-50/60 px-4 py-3 text-xs leading-5 text-blue-900">Reports display backend-returned records only. Missing permissions are reported by the API; this page does not infer authorization from account roles.</div>
  </div>;
}
