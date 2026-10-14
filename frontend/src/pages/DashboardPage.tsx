import { useCallback, useEffect, useState } from "react";
import { Activity, ArrowUpRight, CalendarDays, RefreshCw } from "lucide-react";
import { apiClient, type HealthResponse } from "../api/client";

type HealthState =
  | { status: "loading" }
  | { status: "ready"; data: HealthResponse }
  | { status: "error" };

function formatToday(date: Date): string {
  return new Intl.DateTimeFormat(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  }).format(date);
}

export function DashboardPage() {
  const [health, setHealth] = useState<HealthState>({ status: "loading" });
  const loadHealth = useCallback(async () => {
    setHealth({ status: "loading" });
    try {
      const data = await apiClient.get<HealthResponse>("/health", false);
      setHealth({ status: "ready", data });
    } catch {
      setHealth({ status: "error" });
    }
  }, []);
  useEffect(() => { void loadHealth(); }, [loadHealth]);

  return <div className="space-y-7">
    <section className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
      <div><p className="text-xs font-medium text-slate-400">{formatToday(new Date())}</p><h2 className="mt-2 text-[26px] font-semibold tracking-[-0.035em] text-slate-900 sm:text-[30px]">Welcome to your workspace</h2><p className="mt-2 max-w-xl text-sm leading-6 text-slate-500">Your EPMS starting point for employee and payroll operations.</p></div>
      <div className="inline-flex w-fit items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600 shadow-sm"><CalendarDays size={15} className="text-slate-400" /><span>Today</span></div>
    </section>

    <section aria-label="Workspace status" className="grid gap-4 lg:grid-cols-3">
      <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm lg:col-span-1">
        <div className="flex items-start justify-between"><div><p className="text-xs font-medium text-slate-500">API service</p><div className="mt-3 flex items-center gap-2.5"><span className={`size-2.5 rounded-full ${health.status === "ready" ? "bg-emerald-500" : health.status === "error" ? "bg-rose-500" : "animate-pulse bg-amber-400"}`} /><h3 className="text-lg font-semibold tracking-tight text-slate-900">{health.status === "ready" ? "Available" : health.status === "error" ? "Unreachable" : "Checking…"}</h3></div></div><div className="grid size-9 place-items-center rounded-lg bg-emerald-50 text-emerald-700"><Activity size={17} /></div></div>
        <p className="mt-3 text-xs leading-5 text-slate-500">{health.status === "ready" ? `${health.data.service} responded to its health check.` : health.status === "error" ? "The health endpoint did not respond. Check the backend and retry." : "Contacting the API health endpoint."}</p>
        <p className="mt-3 border-t border-slate-100 pt-3 text-[10px] text-slate-400">Process check only · does not verify database readiness</p>
        {health.status === "error" && <button type="button" onClick={() => void loadHealth()} className="mt-3 inline-flex items-center gap-1.5 text-xs font-semibold text-blue-700 hover:text-blue-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"><RefreshCw size={13} />Retry connection</button>}
      </article>

      <article className="flex flex-col justify-between rounded-xl border border-slate-200 bg-white p-5 shadow-sm lg:col-span-2"><div className="flex items-start justify-between gap-4"><div><p className="text-xs font-medium text-slate-500">Business overview</p><h3 className="mt-2 text-lg font-semibold tracking-tight text-slate-900">Dashboard metrics are not available yet</h3><p className="mt-2 max-w-2xl text-xs leading-6 text-slate-500">The current API does not expose a general dashboard summary. Employee totals, attendance and leave summaries, and payroll overview figures need dedicated reporting endpoints before they can be shown here.</p></div><div className="hidden size-9 shrink-0 place-items-center rounded-lg bg-blue-50 text-blue-700 sm:grid"><ArrowUpRight size={17} /></div></div><div className="mt-5 flex flex-wrap gap-2">{["Employee summary", "Attendance trends", "Leave overview", "Payroll totals"].map((label) => <span key={label} className="rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-[10px] font-medium text-slate-500">{label} · not connected</span>)}</div></article>
    </section>

    <section className="rounded-xl border border-dashed border-slate-300 bg-white/70 px-5 py-8 text-center sm:px-8"><div className="mx-auto grid size-10 place-items-center rounded-xl bg-slate-100 text-slate-500"><Activity size={18} /></div><h3 className="mt-3 text-sm font-semibold text-slate-800">No activity feed is connected</h3><p className="mx-auto mt-1.5 max-w-lg text-xs leading-5 text-slate-500">EPMS does not currently provide a dashboard activity endpoint. This workspace will not display sample or fabricated business activity.</p></section>
  </div>;
}
