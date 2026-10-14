import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { CalendarDays, Check, Plus, Search, X } from "lucide-react";
import { Link } from "react-router-dom";
import { ApiError, apiClient, type LeaveAllocationPage, type LeaveStatus } from "../api/client";
import { CursorPager } from "../components/CursorPager";

interface Filters { date_from: string; date_to: string; employee_id: string; department_id: string; leave_type_id: string; status: "" | LeaveStatus }
interface QueryState { filters: Filters; cursor: string | null; page: number; history: (string | null)[] }
type State = { kind: "loading" } | { kind: "ready"; data: LeaveAllocationPage } | { kind: "error"; message: string };
const empty: Filters = { date_from: "", date_to: "", employee_id: "", department_id: "", leave_type_id: "", status: "" };
const input = "mt-1.5 h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-800 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10";

function buildParams(filters: Filters, cursor: string | null) {
  const params = new URLSearchParams({ limit: "50" });
  for (const key of ["date_from", "date_to", "employee_id", "department_id", "leave_type_id", "status"] as const) if (filters[key]) params.set(key, filters[key]);
  if (cursor) params.set("cursor", cursor);
  return params.toString();
}

export function LeaveAllocationsPage() {
  const [draft, setDraft] = useState(empty);
  const [query, setQuery] = useState<QueryState>({ filters: empty, cursor: null, page: 1, history: [null] });
  const [state, setState] = useState<State>({ kind: "loading" });
  const [reload, setReload] = useState(0);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [reviewComment, setReviewComment] = useState("");
  const requestId = useRef(0);
  const load = useCallback(async () => {
    const id = ++requestId.current; setState({ kind: "loading" });
    try {
      const data = await apiClient.get<LeaveAllocationPage>(`/reports/leave/allocations?${buildParams(query.filters, query.cursor)}`);
      if (requestId.current === id) setState({ kind: "ready", data });
    } catch (error) {
      if (requestId.current === id) setState({ kind: "error", message: error instanceof ApiError && error.status === 403 ? "Your account does not have permission to read organization-wide Leave reports." : error instanceof ApiError ? error.message : "Leave allocations could not be loaded. Check the API connection and try again." });
    }
  }, [query, reload]);
  useEffect(() => { void load(); return () => { requestId.current += 1; }; }, [load]);

  function apply(event: FormEvent) {
    event.preventDefault();
    if (draft.date_from && draft.date_to && draft.date_from > draft.date_to) { setFeedback("Date from must be on or before date to."); return; }
    setFeedback(null); setQuery({ filters: { ...draft }, cursor: null, page: 1, history: [null] });
  }
  function next() {
    if (state.kind !== "ready" || !state.data.pagination.next_cursor) return;
    const cursor = state.data.pagination.next_cursor;
    setQuery((current) => ({ ...current, cursor, page: current.page + 1, history: [...current.history.slice(0, current.page), cursor] }));
  }
  function previous() { if (query.page > 1) { const page = query.page - 1; setQuery((current) => ({ ...current, page, cursor: current.history[page - 1] ?? null, history: current.history.slice(0, page) })); } }
  async function act(requestId: number, action: "approve" | "reject" | "cancel") {
    setBusyId(requestId); setFeedback(null);
    try {
      const body = action === "cancel" ? undefined : { review_comment: reviewComment.trim() || null };
      await apiClient.post(`/leave-requests/${requestId}/${action}`, body);
      setFeedback(`Leave request ${requestId} ${action} action completed.`); setReload((value) => value + 1);
    } catch (error) { setFeedback(error instanceof ApiError ? error.message : `Could not ${action} leave request ${requestId}.`); }
    finally { setBusyId(null); }
  }

  return <div className="space-y-6">
    <section className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end"><div><p className="text-xs font-medium text-slate-400">Workforce</p><h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900">Leave requests</h2><p className="mt-1 text-sm text-slate-500">The report returns one row per persisted daily allocation.</p></div><Link to="/leave/requests/new" className="inline-flex h-10 w-fit items-center gap-2 rounded-lg bg-blue-700 px-4 text-sm font-semibold text-white hover:bg-blue-800"><Plus size={16} />New request</Link></section>
    <nav className="flex gap-2 border-b border-slate-200 pb-2"><Link className="rounded-md bg-blue-50 px-3 py-2 text-xs font-semibold text-blue-700" to="/leave/requests">Allocations</Link><Link className="rounded-md px-3 py-2 text-xs font-semibold text-slate-500 hover:bg-slate-100" to="/leave/balances">Balances</Link></nav>
    <form onSubmit={apply} className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:grid-cols-2 xl:grid-cols-7" aria-label="Leave allocation filters">
      <label className="text-xs font-semibold text-slate-600">Date from<input className={input} type="date" value={draft.date_from} onChange={(e) => setDraft({ ...draft, date_from: e.target.value })} /></label>
      <label className="text-xs font-semibold text-slate-600">Date to<input className={input} type="date" value={draft.date_to} onChange={(e) => setDraft({ ...draft, date_to: e.target.value })} /></label>
      <label className="text-xs font-semibold text-slate-600">Employee ID<input className={input} type="number" min="1" step="1" value={draft.employee_id} onChange={(e) => setDraft({ ...draft, employee_id: e.target.value })} /></label>
      <label className="text-xs font-semibold text-slate-600">Department ID<input className={input} type="number" min="1" step="1" value={draft.department_id} onChange={(e) => setDraft({ ...draft, department_id: e.target.value })} /></label>
      <label className="text-xs font-semibold text-slate-600">Leave type ID<input className={input} type="number" min="1" step="1" value={draft.leave_type_id} onChange={(e) => setDraft({ ...draft, leave_type_id: e.target.value })} /></label>
      <label className="text-xs font-semibold text-slate-600">Status<select className={input} value={draft.status} onChange={(e) => setDraft({ ...draft, status: e.target.value as Filters["status"] })}><option value="">All statuses</option>{(["PENDING", "APPROVED", "REJECTED", "CANCELLED"] as const).map((status) => <option key={status}>{status}</option>)}</select></label>
      <div className="flex items-end gap-2"><button className="inline-flex h-10 flex-1 items-center justify-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"><Search size={15} />Apply</button><button type="button" onClick={() => { setDraft(empty); setQuery({ filters: empty, cursor: null, page: 1, history: [null] }); setFeedback(null); }} className="h-10 px-2 text-sm text-slate-500">Clear</button></div>
    </form>
    <div className="rounded-lg border border-blue-100 bg-blue-50/60 px-4 py-3 text-xs leading-5 text-blue-900">Leave type names are shown from persisted report data. There is no leave-type list endpoint, so creation forms use a type ID. The API validates employee ownership and permissions; client-entered IDs do not establish authorization.</div>
    <label className="block max-w-xl text-xs font-medium text-slate-600">Review comment (optional)<input className={input} maxLength={1000} value={reviewComment} onChange={(e) => setReviewComment(e.target.value)} placeholder="Used when approving or rejecting" /></label>
    {feedback && <div role="status" className="rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700">{feedback}</div>}
    {state.kind === "loading" && <div role="status" className="rounded-xl border border-slate-200 bg-white p-10 text-center text-sm text-slate-500">Loading Leave allocations…</div>}
    {state.kind === "error" && <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-800"><p className="font-semibold">Leave report unavailable</p><p className="mt-1">{state.message}</p><button type="button" className="mt-3 font-semibold underline" onClick={() => setReload((value) => value + 1)}>Retry</button></div>}
    {state.kind === "ready" && state.data.allocations.length === 0 && <div className="rounded-xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center"><CalendarDays className="mx-auto text-slate-400" size={24} /><h3 className="mt-3 text-sm font-semibold text-slate-800">No Leave allocations found</h3><p className="mt-1 text-sm text-slate-500">No persisted allocation rows match these filters.</p></div>}
    {state.kind === "ready" && state.data.allocations.length > 0 && <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm"><div className="overflow-x-auto"><table className="w-full min-w-[1150px] text-left text-sm"><thead className="bg-slate-50 text-[11px] uppercase tracking-wide text-slate-500"><tr>{["Request / employee", "Leave type", "Allocation date", "Fraction", "Request status", "Request period / requested days", "Action"].map((label) => <th key={label} className="px-4 py-3 font-semibold">{label}</th>)}</tr></thead><tbody className="divide-y divide-slate-100">{state.data.allocations.map((row) => <tr key={row.leave_request_day_id} className="align-top hover:bg-slate-50/70"><td className="px-4 py-4"><p className="font-semibold text-slate-800">{row.first_name} {row.last_name}</p><p className="mt-0.5 text-xs text-slate-400">Request {row.leave_request_id} · {row.employee_code} · Employee {row.employee_id}</p></td><td className="px-4 py-4 text-slate-700">{row.leave_type_name}<p className="mt-0.5 text-xs text-slate-400">Type {row.leave_type_id}</p></td><td className="px-4 py-4 text-slate-600">{row.leave_date}</td><td className="px-4 py-4 text-slate-600">{row.day_fraction}</td><td className="px-4 py-4"><span className="rounded-full bg-slate-100 px-2.5 py-1 text-[10px] font-semibold text-slate-600">{row.status}</span></td><td className="px-4 py-4 text-slate-600">{row.start_date} – {row.end_date}<p className="mt-0.5 text-xs text-slate-400">requested_days: {row.requested_days} (repeated per allocation; not a request total here)</p></td><td className="px-4 py-4">{row.status === "PENDING" && <div className="flex gap-1"><button disabled={busyId === row.leave_request_id} aria-label={`Approve request ${row.leave_request_id}`} onClick={() => void act(row.leave_request_id, "approve")} className="rounded-md p-1.5 text-emerald-700 hover:bg-emerald-50 disabled:opacity-40"><Check size={15} /></button><button disabled={busyId === row.leave_request_id} aria-label={`Reject request ${row.leave_request_id}`} onClick={() => void act(row.leave_request_id, "reject")} className="rounded-md p-1.5 text-rose-700 hover:bg-rose-50 disabled:opacity-40"><X size={15} /></button><button disabled={busyId === row.leave_request_id} onClick={() => void act(row.leave_request_id, "cancel")} className="rounded-md px-2 py-1 text-[10px] font-semibold text-slate-500 hover:bg-slate-100 disabled:opacity-40">Cancel</button></div>}{row.status === "APPROVED" && <button disabled={busyId === row.leave_request_id} onClick={() => void act(row.leave_request_id, "cancel")} className="rounded-md px-2 py-1 text-[10px] font-semibold text-slate-500 hover:bg-slate-100 disabled:opacity-40">Cancel</button>}</td></tr>)}</tbody></table></div><CursorPager page={query.page} limit={state.data.pagination.limit} hasMore={state.data.pagination.has_more} onPrevious={previous} onNext={next} /></div>}
    <p className="text-xs text-slate-400">Review and cancel actions are sent to the API, which enforces the corresponding persisted permission and lifecycle rules.</p>
  </div>;
}
