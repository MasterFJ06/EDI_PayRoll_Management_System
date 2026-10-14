import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { ArrowDown, ArrowUp, Plus, Search, UsersRound } from "lucide-react";
import { Link } from "react-router-dom";
import { ApiError, apiClient, type EmployeeReportPage } from "../api/client";

type EmploymentStatus = "" | "ACTIVE" | "INACTIVE" | "TERMINATED";
interface Filters { employee_code: string; department_id: string; designation_id: string; employment_status: EmploymentStatus }
interface QueryState { filters: Filters; cursor: string | null; page: number; cursorHistory: (string | null)[] }
type LoadState = { status: "loading" } | { status: "ready"; data: EmployeeReportPage } | { status: "error"; message: string };

const emptyFilters: Filters = { employee_code: "", department_id: "", designation_id: "", employment_status: "" };
const inputClass = "h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-800 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10";

function queryString(filters: Filters, cursor: string | null): string {
  const params = new URLSearchParams({ limit: "50" });
  for (const key of ["employee_code", "department_id", "designation_id", "employment_status"] as const) {
    const value = filters[key];
    if (value) params.set(key, value);
  }
  if (cursor) params.set("cursor", cursor);
  return params.toString();
}

function failureMessage(error: unknown): string {
  if (error instanceof ApiError && error.status === 403) return "Your account does not have permission to read the employee directory.";
  return error instanceof ApiError ? error.message : "The employee report could not be loaded. Check the API connection and try again.";
}

export function EmployeeDirectoryPage() {
  const [draft, setDraft] = useState<Filters>(emptyFilters);
  const [query, setQuery] = useState<QueryState>({ filters: emptyFilters, cursor: null, page: 1, cursorHistory: [null] });
  const [reloadKey, setReloadKey] = useState(0);
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const requestId = useRef(0);

  const load = useCallback(async () => {
    const currentRequest = ++requestId.current;
    setState({ status: "loading" });
    try {
      const data = await apiClient.get<EmployeeReportPage>(`/reports/employees?${queryString(query.filters, query.cursor)}`);
      if (requestId.current === currentRequest) setState({ status: "ready", data });
    } catch (error) {
      if (requestId.current === currentRequest) setState({ status: "error", message: failureMessage(error) });
    }
  }, [query, reloadKey]);

  useEffect(() => { void load(); return () => { requestId.current += 1; }; }, [load]);

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalized = { ...draft, employee_code: draft.employee_code.trim() };
    setDraft(normalized);
    setQuery({ filters: normalized, cursor: null, page: 1, cursorHistory: [null] });
  }

  function nextPage() {
    if (state.status !== "ready" || !state.data.pagination.next_cursor) return;
    const cursor = state.data.pagination.next_cursor;
    setQuery((current) => ({ ...current, cursor, page: current.page + 1, cursorHistory: [...current.cursorHistory.slice(0, current.page), cursor] }));
  }

  function previousPage() {
    if (query.page <= 1) return;
    const page = query.page - 1;
    setQuery((current) => ({ ...current, page, cursor: current.cursorHistory[page - 1] ?? null, cursorHistory: current.cursorHistory.slice(0, page) }));
  }

  return <div className="space-y-6">
    <section className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
      <div><p className="text-xs font-medium text-slate-400">People operations</p><h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900">Employee directory</h2><p className="mt-1 text-sm text-slate-500">Browse persisted employee records. Search by exact employee code.</p></div>
      <Link to="/employees/new" className="inline-flex h-10 w-fit items-center gap-2 rounded-lg bg-blue-700 px-4 text-sm font-semibold text-white hover:bg-blue-800 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-blue-600/20"><Plus size={16} />Add employee</Link>
    </section>

    <form onSubmit={applyFilters} className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:grid-cols-2 xl:grid-cols-5" aria-label="Employee directory filters">
      <label className="text-xs font-medium text-slate-600">Exact employee code<input className={`${inputClass} mt-1.5`} maxLength={30} value={draft.employee_code} onChange={(e) => setDraft({ ...draft, employee_code: e.target.value })} placeholder="e.g. EMP-104" /></label>
      <label className="text-xs font-medium text-slate-600">Department ID<input className={`${inputClass} mt-1.5`} type="number" min="1" step="1" value={draft.department_id} onChange={(e) => setDraft({ ...draft, department_id: e.target.value })} placeholder="Any department" /></label>
      <label className="text-xs font-medium text-slate-600">Designation ID<input className={`${inputClass} mt-1.5`} type="number" min="1" step="1" value={draft.designation_id} onChange={(e) => setDraft({ ...draft, designation_id: e.target.value })} placeholder="Any designation" /></label>
      <label className="text-xs font-medium text-slate-600">Employment status<select className={`${inputClass} mt-1.5`} value={draft.employment_status} onChange={(e) => setDraft({ ...draft, employment_status: e.target.value as EmploymentStatus })}><option value="">All statuses</option><option>ACTIVE</option><option>INACTIVE</option><option>TERMINATED</option></select></label>
      <div className="flex items-end gap-2"><button type="submit" className="inline-flex h-10 flex-1 items-center justify-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"><Search size={15} />Apply</button><button type="button" onClick={() => { setDraft(emptyFilters); setQuery({ filters: emptyFilters, cursor: null, page: 1, cursorHistory: [null] }); }} className="h-10 rounded-lg px-3 text-sm font-medium text-slate-500 hover:bg-slate-50">Clear</button></div>
    </form>

    {state.status === "loading" && <div className="rounded-xl border border-slate-200 bg-white p-10 text-center text-sm text-slate-500" role="status">Loading employee records…</div>}
    {state.status === "error" && <div className="rounded-xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-800" role="alert"><p className="font-semibold">Could not load employees</p><p className="mt-1">{state.message}</p><button type="button" onClick={() => setReloadKey((key) => key + 1)} className="mt-3 font-semibold underline">Retry</button></div>}
    {state.status === "ready" && state.data.employees.length === 0 && <div className="rounded-xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center"><UsersRound className="mx-auto text-slate-400" size={24} /><h3 className="mt-3 text-sm font-semibold text-slate-800">No employees found</h3><p className="mt-1 text-sm text-slate-500">Try changing the exact filters or add an employee.</p></div>}
    {state.status === "ready" && state.data.employees.length > 0 && <>
      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="overflow-x-auto"><table className="w-full min-w-[850px] text-left text-sm"><thead className="bg-slate-50 text-[11px] uppercase tracking-wide text-slate-500"><tr><th className="px-5 py-3 font-semibold">Employee</th><th className="px-5 py-3 font-semibold">Department</th><th className="px-5 py-3 font-semibold">Designation</th><th className="px-5 py-3 font-semibold">Joined</th><th className="px-5 py-3 font-semibold">Status</th><th className="px-5 py-3"><span className="sr-only">Actions</span></th></tr></thead>
          <tbody className="divide-y divide-slate-100">{state.data.employees.map((employee) => <tr key={employee.employee_id} className="hover:bg-slate-50/70"><td className="px-5 py-4"><Link className="font-semibold text-slate-800 hover:text-blue-700" to={`/employees/${encodeURIComponent(employee.employee_code)}`}>{employee.first_name} {employee.last_name}</Link><p className="mt-0.5 text-xs text-slate-400">{employee.employee_code} · ID {employee.employee_id}</p></td><td className="px-5 py-4 text-slate-600">{employee.department_name ?? `Department ${employee.department_id}`}</td><td className="px-5 py-4 text-slate-600">{employee.designation_name ?? `Designation ${employee.designation_id}`}</td><td className="px-5 py-4 text-slate-600">{employee.joining_date}</td><td className="px-5 py-4"><span className="rounded-full bg-slate-100 px-2.5 py-1 text-[10px] font-semibold text-slate-600">{employee.employment_status}</span></td><td className="px-5 py-4 text-right"><Link to={`/employees/${encodeURIComponent(employee.employee_code)}`} className="text-xs font-semibold text-blue-700 hover:underline">View</Link></td></tr>)}</tbody>
        </table></div>
        <div className="flex items-center justify-between border-t border-slate-100 px-4 py-3"><span className="text-xs text-slate-500">Page {query.page} · {state.data.pagination.limit} per page</span><div className="flex gap-2"><button type="button" disabled={query.page <= 1} onClick={previousPage} className="inline-flex h-8 items-center gap-1 rounded-md border border-slate-200 px-2.5 text-xs font-medium text-slate-600 disabled:opacity-40"><ArrowUp size={13} />Previous</button><button type="button" disabled={!state.data.pagination.has_more} onClick={nextPage} className="inline-flex h-8 items-center gap-1 rounded-md border border-slate-200 px-2.5 text-xs font-medium text-slate-600 disabled:opacity-40">Next<ArrowDown size={13} /></button></div></div>
      </div>
    </>}
  </div>;
}
