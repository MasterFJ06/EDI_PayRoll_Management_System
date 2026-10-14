import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { Plus, Search, Wallet } from "lucide-react";
import { Link } from "react-router-dom";
import { ApiError, apiClient, type LeaveBalancePage } from "../api/client";
import { CursorPager } from "../components/CursorPager";

interface Filters { employee_id: string; department_id: string; leave_type_id: string; balance_year: string }
interface QueryState { filters: Filters; cursor: string | null; page: number; history: (string | null)[] }
type State = { kind: "loading" } | { kind: "ready"; data: LeaveBalancePage } | { kind: "error"; message: string };
const empty: Filters = { employee_id: "", department_id: "", leave_type_id: "", balance_year: "" };
const input = "mt-1.5 h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-800 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10";

function makeParams(filters: Filters, cursor: string | null) {
  const params = new URLSearchParams({ limit: "50" });
  for (const key of ["employee_id", "department_id", "leave_type_id", "balance_year"] as const) if (filters[key] !== "") params.set(key, filters[key]);
  if (cursor) params.set("cursor", cursor);
  return params.toString();
}

export function LeaveBalancesPage() {
  const [draft, setDraft] = useState(empty);
  const [query, setQuery] = useState<QueryState>({ filters: empty, cursor: null, page: 1, history: [null] });
  const [state, setState] = useState<State>({ kind: "loading" });
  const [reload, setReload] = useState(0);
  const requestId = useRef(0);
  const load = useCallback(async () => {
    const id = ++requestId.current; setState({ kind: "loading" });
    try {
      const data = await apiClient.get<LeaveBalancePage>(`/reports/leave/balances?${makeParams(query.filters, query.cursor)}`);
      if (requestId.current === id) setState({ kind: "ready", data });
    } catch (error) {
      if (requestId.current === id) setState({ kind: "error", message: error instanceof ApiError && error.status === 403 ? "Your account does not have permission to read organization-wide Leave balances." : error instanceof ApiError ? error.message : "Leave balances could not be loaded. Check the API connection and try again." });
    }
  }, [query, reload]);
  useEffect(() => { void load(); return () => { requestId.current += 1; }; }, [load]);
  function apply(event: FormEvent) { event.preventDefault(); setQuery({ filters: { ...draft }, cursor: null, page: 1, history: [null] }); }
  function next() { if (state.kind === "ready" && state.data.pagination.next_cursor) { const cursor = state.data.pagination.next_cursor; setQuery((current) => ({ ...current, cursor, page: current.page + 1, history: [...current.history.slice(0, current.page), cursor] })); } }
  function previous() { if (query.page > 1) { const page = query.page - 1; setQuery((current) => ({ ...current, page, cursor: current.history[page - 1] ?? null, history: current.history.slice(0, page) })); } }
  return <div className="space-y-6">
    <section className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end"><div><p className="text-xs font-medium text-slate-400">Workforce</p><h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900">Leave balances</h2><p className="mt-1 text-sm text-slate-500">Persisted allocated and used values; no remaining balance is calculated.</p></div><Link to="/leave/balances/new" className="inline-flex h-10 w-fit items-center gap-2 rounded-lg bg-blue-700 px-4 text-sm font-semibold text-white hover:bg-blue-800"><Plus size={16} />Create balance</Link></section>
    <nav className="flex gap-2 border-b border-slate-200 pb-2"><Link className="rounded-md px-3 py-2 text-xs font-semibold text-slate-500 hover:bg-slate-100" to="/leave/requests">Allocations</Link><Link className="rounded-md bg-blue-50 px-3 py-2 text-xs font-semibold text-blue-700" to="/leave/balances">Balances</Link></nav>
    <form onSubmit={apply} className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:grid-cols-2 xl:grid-cols-5" aria-label="Leave balance filters"><label className="text-xs font-semibold text-slate-600">Employee ID<input className={input} type="number" min="1" step="1" value={draft.employee_id} onChange={(e) => setDraft({ ...draft, employee_id: e.target.value })} /></label><label className="text-xs font-semibold text-slate-600">Department ID<input className={input} type="number" min="1" step="1" value={draft.department_id} onChange={(e) => setDraft({ ...draft, department_id: e.target.value })} /></label><label className="text-xs font-semibold text-slate-600">Leave type ID<input className={input} type="number" min="1" step="1" value={draft.leave_type_id} onChange={(e) => setDraft({ ...draft, leave_type_id: e.target.value })} /></label><label className="text-xs font-semibold text-slate-600">Stored balance year<input className={input} type="number" min="0" max="65535" step="1" value={draft.balance_year} onChange={(e) => setDraft({ ...draft, balance_year: e.target.value })} /></label><div className="flex items-end gap-2"><button className="inline-flex h-10 flex-1 items-center justify-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"><Search size={15} />Apply</button><button type="button" onClick={() => { setDraft(empty); setQuery({ filters: empty, cursor: null, page: 1, history: [null] }); }} className="h-10 px-2 text-sm text-slate-500">Clear</button></div></form>
    <p className="text-xs text-slate-400">Leave type names are current labels. `balance_year` is displayed as stored; the API does not define it as a calendar or employment year. Access requires the API’s persisted report permission.</p>
    {state.kind === "loading" && <div role="status" className="rounded-xl border border-slate-200 bg-white p-10 text-center text-sm text-slate-500">Loading Leave balances…</div>}
    {state.kind === "error" && <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-800"><p className="font-semibold">Leave balances unavailable</p><p className="mt-1">{state.message}</p><button type="button" className="mt-3 font-semibold underline" onClick={() => setReload((value) => value + 1)}>Retry</button></div>}
    {state.kind === "ready" && state.data.balances.length === 0 && <div className="rounded-xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center"><Wallet className="mx-auto text-slate-400" size={24} /><h3 className="mt-3 text-sm font-semibold text-slate-800">No balances found</h3><p className="mt-1 text-sm text-slate-500">No persisted balance rows match these filters.</p></div>}
    {state.kind === "ready" && state.data.balances.length > 0 && <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm"><div className="overflow-x-auto"><table className="w-full min-w-[850px] text-left text-sm"><thead className="bg-slate-50 text-[11px] uppercase tracking-wide text-slate-500"><tr>{["Employee", "Leave type", "Stored year", "Allocated days", "Used days"].map((label) => <th key={label} className="px-5 py-3 font-semibold">{label}</th>)}</tr></thead><tbody className="divide-y divide-slate-100">{state.data.balances.map((row) => <tr key={`${row.employee_id}:${row.leave_type_id}:${row.balance_year}`} className="hover:bg-slate-50/70"><td className="px-5 py-4"><p className="font-semibold text-slate-800">{row.first_name} {row.last_name}</p><p className="mt-0.5 text-xs text-slate-400">{row.employee_code} · Employee {row.employee_id}</p></td><td className="px-5 py-4 text-slate-700">{row.leave_type_name}<p className="mt-0.5 text-xs text-slate-400">Type {row.leave_type_id}</p></td><td className="px-5 py-4 text-slate-600">{row.balance_year}</td><td className="px-5 py-4 text-slate-600">{row.allocated_days}</td><td className="px-5 py-4 text-slate-600">{row.used_days}</td></tr>)}</tbody></table></div><CursorPager page={query.page} limit={state.data.pagination.limit} hasMore={state.data.pagination.has_more} onPrevious={previous} onNext={next} /></div>}
  </div>;
}
