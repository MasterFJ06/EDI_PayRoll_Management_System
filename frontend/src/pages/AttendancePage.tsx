import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { CalendarDays, Clock3, Plus, Search } from "lucide-react";
import { Link } from "react-router-dom";
import { ApiError, apiClient, type AttendanceReportPage, type AttendanceStatus } from "../api/client";
import { CursorPager } from "../components/CursorPager";

interface Filters { date_from: string; date_to: string; employee_id: string; department_id: string; attendance_status: "" | AttendanceStatus }
interface QueryState { filters: Filters; cursor: string | null; page: number; history: (string | null)[] }
type LoadState = { kind: "loading" } | { kind: "ready"; data: AttendanceReportPage } | { kind: "error"; message: string };
const empty: Filters = { date_from: "", date_to: "", employee_id: "", department_id: "", attendance_status: "" };
const inputClass = "mt-1.5 h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-800 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10";

function paramsFor(filters: Filters, cursor: string | null): string {
  const params = new URLSearchParams({ limit: "50" });
  for (const key of ["date_from", "date_to", "employee_id", "department_id", "attendance_status"] as const) if (filters[key]) params.set(key, filters[key]);
  if (cursor) params.set("cursor", cursor);
  return params.toString();
}

export function AttendancePage() {
  const [draft, setDraft] = useState(empty);
  const [query, setQuery] = useState<QueryState>({ filters: empty, cursor: null, page: 1, history: [null] });
  const [state, setState] = useState<LoadState>({ kind: "loading" });
  const [reload, setReload] = useState(0);
  const requestId = useRef(0);
  const load = useCallback(async () => {
    const id = ++requestId.current;
    setState({ kind: "loading" });
    try {
      const data = await apiClient.get<AttendanceReportPage>(`/reports/attendance?${paramsFor(query.filters, query.cursor)}`);
      if (requestId.current === id) setState({ kind: "ready", data });
    } catch (error) {
      if (requestId.current === id) setState({ kind: "error", message: error instanceof ApiError && error.status === 403 ? "Your account does not have permission to read attendance reports." : error instanceof ApiError ? error.message : "The attendance report could not be loaded. Check the API connection and try again." });
    }
  }, [query, reload]);
  useEffect(() => { void load(); return () => { requestId.current += 1; }; }, [load]);

  function apply(event: FormEvent) {
    event.preventDefault();
    if (draft.date_from && draft.date_to && draft.date_from > draft.date_to) {
      setState({ kind: "error", message: "Start date must be on or before end date." });
      return;
    }
    setQuery({ filters: { ...draft }, cursor: null, page: 1, history: [null] });
  }
  function next() {
    if (state.kind !== "ready" || !state.data.pagination.next_cursor) return;
    const cursor = state.data.pagination.next_cursor;
    setQuery((current) => ({ ...current, cursor, page: current.page + 1, history: [...current.history.slice(0, current.page), cursor] }));
  }
  function previous() {
    if (query.page <= 1) return;
    const page = query.page - 1;
    setQuery((current) => ({ ...current, page, cursor: current.history[page - 1] ?? null, history: current.history.slice(0, page) }));
  }

  return <div className="space-y-6">
    <section className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end"><div><p className="text-xs font-medium text-slate-400">Workforce</p><h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900">Attendance</h2><p className="mt-1 text-sm text-slate-500">Persisted attendance records and clock times.</p></div><Link to="/attendance/new" className="inline-flex h-10 w-fit items-center gap-2 rounded-lg bg-blue-700 px-4 text-sm font-semibold text-white hover:bg-blue-800"><Plus size={16} />Record attendance</Link></section>
    <form onSubmit={apply} className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:grid-cols-2 xl:grid-cols-6" aria-label="Attendance filters">
      <label className="text-xs font-semibold text-slate-600">Date from<input className={inputClass} type="date" value={draft.date_from} onChange={(e) => setDraft({ ...draft, date_from: e.target.value })} /></label>
      <label className="text-xs font-semibold text-slate-600">Date to<input className={inputClass} type="date" value={draft.date_to} onChange={(e) => setDraft({ ...draft, date_to: e.target.value })} /></label>
      <label className="text-xs font-semibold text-slate-600">Employee ID<input className={inputClass} type="number" min="1" step="1" value={draft.employee_id} onChange={(e) => setDraft({ ...draft, employee_id: e.target.value })} /></label>
      <label className="text-xs font-semibold text-slate-600">Department ID<input className={inputClass} type="number" min="1" step="1" value={draft.department_id} onChange={(e) => setDraft({ ...draft, department_id: e.target.value })} /></label>
      <label className="text-xs font-semibold text-slate-600">Status<select className={inputClass} value={draft.attendance_status} onChange={(e) => setDraft({ ...draft, attendance_status: e.target.value as Filters["attendance_status"] })}><option value="">All statuses</option>{(["PRESENT", "ABSENT", "HALF_DAY", "ON_LEAVE", "HOLIDAY"] as const).map((status) => <option key={status}>{status}</option>)}</select></label>
      <div className="flex items-end gap-2"><button className="inline-flex h-10 flex-1 items-center justify-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"><Search size={15} />Apply</button><button type="button" onClick={() => { setDraft(empty); setQuery({ filters: empty, cursor: null, page: 1, history: [null] }); }} className="h-10 px-2 text-sm text-slate-500">Clear</button></div>
    </form>
    {state.kind === "loading" && <div role="status" className="rounded-xl border border-slate-200 bg-white p-10 text-center text-sm text-slate-500">Loading attendance records…</div>}
    {state.kind === "error" && <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-800"><p className="font-semibold">Attendance unavailable</p><p className="mt-1">{state.message}</p><button type="button" className="mt-3 font-semibold underline" onClick={() => setReload((value) => value + 1)}>Retry</button></div>}
    {state.kind === "ready" && state.data.attendance_records.length === 0 && <div className="rounded-xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center"><CalendarDays className="mx-auto text-slate-400" size={24} /><h3 className="mt-3 text-sm font-semibold text-slate-800">No attendance records found</h3><p className="mt-1 text-sm text-slate-500">No persisted attendance records match these filters.</p></div>}
    {state.kind === "ready" && state.data.attendance_records.length > 0 && <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm"><div className="overflow-x-auto"><table className="w-full min-w-[920px] text-left text-sm"><thead className="bg-slate-50 text-[11px] uppercase tracking-wide text-slate-500"><tr>{["Employee", "Date", "Status", "Clock in", "Clock out", "Department / designation"].map((header) => <th key={header} className="px-5 py-3 font-semibold">{header}</th>)}</tr></thead><tbody className="divide-y divide-slate-100">{state.data.attendance_records.map((row) => <tr key={row.attendance_id} className="hover:bg-slate-50/70"><td className="px-5 py-4"><p className="font-semibold text-slate-800">{row.first_name} {row.last_name}</p><p className="mt-0.5 text-xs text-slate-400">{row.employee_code} · Employee {row.employee_id} · Record {row.attendance_id}</p></td><td className="px-5 py-4 text-slate-600">{row.attendance_date}</td><td className="px-5 py-4"><span className="rounded-full bg-slate-100 px-2.5 py-1 text-[10px] font-semibold text-slate-600">{row.attendance_status}</span></td><td className="px-5 py-4 text-slate-600"><Clock3 className="mr-1 inline" size={13} />{row.check_in_time ?? "—"}</td><td className="px-5 py-4 text-slate-600"><Clock3 className="mr-1 inline" size={13} />{row.check_out_time ?? "—"}</td><td className="px-5 py-4 text-slate-600">{row.department_name ?? `Department ${row.department_id}`}<p className="mt-0.5 text-xs text-slate-400">{row.designation_name ?? `Designation ${row.designation_id}`}</p></td></tr>)}</tbody></table></div><CursorPager page={query.page} limit={state.data.pagination.limit} hasMore={state.data.pagination.has_more} onPrevious={previous} onNext={next} /></div>}
    <p className="text-xs text-slate-400">The attendance report requires the persisted `report.attendance.read` permission. The API checks access; navigation visibility does not grant it.</p>
  </div>;
}
