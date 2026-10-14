import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { Activity, CheckCircle2, FileText, Play, RefreshCw, RotateCcw, ShieldAlert } from "lucide-react";
import { ApiError, apiClient, type FinalizedPayrollSummary, type PayrollComponentReportPage, type PayrollResultReportPage, type PayrollRun, type PayrollRunStatus, type PayslipCreateResponse } from "../api/client";
import { CursorPager } from "../components/CursorPager";

type ReportTab = "summary" | "results" | "components";
type PayslipOutcome = { response?: PayslipCreateResponse; error?: string };
type ComponentFilters = { employee_id: string; salary_component_id: string; component_type: "" | "EARNING" | "DEDUCTION" };
type ReportState = { kind: "idle" | "loading" } | { kind: "error"; message: string } | { kind: "summary"; data: FinalizedPayrollSummary } | { kind: "results"; data: PayrollResultReportPage } | { kind: "components"; data: PayrollComponentReportPage };
const input = "mt-1.5 h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-800 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10";
const statusStyles: Record<PayrollRunStatus, string> = {
  CREATED: "bg-sky-50 text-sky-700", PROCESSING: "bg-amber-50 text-amber-800", FAILED: "bg-rose-50 text-rose-700",
  PROCESSED: "bg-violet-50 text-violet-700", FINALIZED: "bg-emerald-50 text-emerald-700",
};
const actionLabels = { process: "Process run", retry: "Retry failed run", recover: "Recover expired attempt", finalize: "Finalize run" } as const;
const emptyComponentFilters: ComponentFilters = { employee_id: "", salary_component_id: "", component_type: "" };

function errorText(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) return "Your session is no longer valid. Sign in again.";
    if (error.status === 403) return "Your account does not have the persisted permission required for this operation.";
    return error.message;
  }
  return "The API request could not be completed. Check the connection and refresh the run before retrying.";
}

function money(value: number | string): string {
  const amount = String(value);
  const match = /^(-?\d+)(?:\.(\d+))?$/.exec(amount);
  return match ? `${match[1]}.${(match[2] ?? "").padEnd(2, "0")}` : amount;
}

export function PayrollPage() {
  const now = new Date();
  const [year, setYear] = useState(String(now.getFullYear()));
  const [month, setMonth] = useState(String(now.getMonth() + 1));
  const [lookupId, setLookupId] = useState("");
  const [run, setRun] = useState<PayrollRun | null>(null);
  const [runBusy, setRunBusy] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [activeAction, setActiveAction] = useState<keyof typeof actionLabels | null>(null);
  const [tab, setTab] = useState<ReportTab>("summary");
  const [cursor, setCursor] = useState<string | null>(null);
  const [cursorHistory, setCursorHistory] = useState<(string | null)[]>([null]);
  const [page, setPage] = useState(1);
  const [reportReload, setReportReload] = useState(0);
  const [report, setReport] = useState<ReportState>({ kind: "idle" });
  const [payslipTarget, setPayslipTarget] = useState<number | null>(null);
  const [payslipNumber, setPayslipNumber] = useState("");
  const [payslipBusyId, setPayslipBusyId] = useState<number | null>(null);
  const [payslips, setPayslips] = useState<Record<number, PayslipOutcome>>({});
  const [componentFilterDraft, setComponentFilterDraft] = useState<ComponentFilters>(emptyComponentFilters);
  const [componentFilters, setComponentFilters] = useState<ComponentFilters>(emptyComponentFilters);
  const [componentFilterError, setComponentFilterError] = useState<string | null>(null);
  const reportRequest = useRef(0);

  const refreshRun = useCallback(async (id: number) => {
    setRunBusy(true); setRunError(null);
    try { const current = await apiClient.getPayrollRun(id); setRun(current); setLookupId(String(current.payroll_run_id)); return current; }
    catch (error) { setRunError(errorText(error)); throw error; }
    finally { setRunBusy(false); }
  }, []);

  async function createRun(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setRunBusy(true); setRunError(null); setNotice(null);
    try {
      const created = await apiClient.createPayrollRun({ year: Number(year), month: Number(month) });
      setRun(created); setLookupId(String(created.payroll_run_id)); setNotice(`Payroll Run ${created.payroll_run_id} was created.`);
    } catch (error) { setRunError(errorText(error)); }
    finally { setRunBusy(false); }
  }

  async function retrieveRun(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!/^\d+$/.test(lookupId) || Number(lookupId) < 1) { setRunError("Enter a positive Payroll Run ID."); return; }
    setNotice(null);
    try { await refreshRun(Number(lookupId)); }
    catch { /* refreshRun presents the API error */ }
  }

  async function performAction(action: keyof typeof actionLabels) {
    if (!run || activeAction) return;
    const confirmation = action === "finalize"
      ? "Finalize this processed Payroll Run? Finalization is terminal."
      : action === "recover"
        ? "Request recovery of this processing attempt? Recovery succeeds only if the backend confirms its lease has expired."
        : `${actionLabels[action]} for Payroll Run ${run.payroll_run_id}?`;
    if (!window.confirm(confirmation)) return;
    setActiveAction(action); setRunError(null); setNotice(null);
    try {
      await apiClient.payrollRunAction(run.payroll_run_id, action);
      const updated = await apiClient.getPayrollRun(run.payroll_run_id);
      setRun(updated); setNotice(`${actionLabels[action]} completed. Current status: ${updated.status}.`);
      setCursor(null); setCursorHistory([null]); setPage(1); setReportReload((value) => value + 1);
    } catch (error) {
      setRunError(`${errorText(error)} The request may have reached the server; refreshing the run status.`);
      try { const updated = await apiClient.getPayrollRun(run.payroll_run_id); setRun(updated); }
      catch { /* keep the original operation error visible */ }
    } finally { setActiveAction(null); }
  }

  const loadReport = useCallback(async () => {
    if (!run || run.status !== "FINALIZED") { setReport({ kind: "idle" }); return; }
    const requestId = ++reportRequest.current;
    setReport({ kind: "loading" });
    try {
      if (tab === "summary") {
        const data = await apiClient.get<FinalizedPayrollSummary>(`/reports/payroll/runs/${run.payroll_run_id}`);
        if (reportRequest.current === requestId) setReport({ kind: "summary", data });
      } else {
        const params = new URLSearchParams({ limit: "50" }); if (cursor) params.set("cursor", cursor);
        if (tab === "results") {
          const data = await apiClient.get<PayrollResultReportPage>(`/reports/payroll/runs/${run.payroll_run_id}/results?${params}`);
          if (reportRequest.current === requestId) setReport({ kind: "results", data });
        } else {
          for (const key of ["employee_id", "salary_component_id", "component_type"] as const) {
            if (componentFilters[key]) params.set(key, componentFilters[key]);
          }
          const data = await apiClient.get<PayrollComponentReportPage>(`/reports/payroll/runs/${run.payroll_run_id}/components?${params}`);
          if (reportRequest.current === requestId) setReport({ kind: "components", data });
        }
      }
    } catch (error) {
      if (reportRequest.current === requestId) setReport({ kind: "error", message: errorText(error) });
    }
  }, [run, tab, cursor, reportReload, componentFilters]);

  useEffect(() => { void loadReport(); return () => { reportRequest.current += 1; }; }, [loadReport]);

  function chooseTab(next: ReportTab) { setTab(next); setCursor(null); setCursorHistory([null]); setPage(1); }
  function applyComponentFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    for (const key of ["employee_id", "salary_component_id"] as const) {
      const value = componentFilterDraft[key];
      if (value && (!/^\d+$/.test(value) || Number(value) < 1)) { setComponentFilterError("Enter positive whole-number IDs or leave the filter empty."); return; }
    }
    setComponentFilterError(null);
    setComponentFilters({ ...componentFilterDraft }); setCursor(null); setCursorHistory([null]); setPage(1);
  }
  function nextPage(hasMore: boolean, nextCursor: string | null) {
    if (!hasMore || !nextCursor) return;
    setCursor(nextCursor); setPage((current) => current + 1);
    setCursorHistory((history) => [...history.slice(0, page), nextCursor]);
  }
  function previousPage() {
    if (page <= 1) return;
    const previous = page - 1; setPage(previous); setCursor(cursorHistory[previous - 1] ?? null);
    setCursorHistory((history) => history.slice(0, previous));
  }

  async function generatePayslip(event: FormEvent<HTMLFormElement>, resultId: number) {
    event.preventDefault();
    if (!run || payslipBusyId !== null || !window.confirm(`Create a payslip record for Payroll Result ${resultId}? This does not generate a PDF.`)) return;
    setPayslipBusyId(resultId); setPayslips((current) => ({ ...current, [resultId]: {} }));
    try {
      const response = await apiClient.createPayslip(run.payroll_run_id, resultId, payslipNumber);
      setPayslips((current) => ({ ...current, [resultId]: { response } }));
      setPayslipTarget(null); setPayslipNumber("");
    } catch (error) { setPayslips((current) => ({ ...current, [resultId]: { error: errorText(error) } })); }
    finally { setPayslipBusyId(null); }
  }

  const actions: (keyof typeof actionLabels)[] = run?.status === "CREATED" ? ["process"]
    : run?.status === "PROCESSING" ? ["recover"]
      : run?.status === "FAILED" ? ["retry"]
        : run?.status === "PROCESSED" ? ["finalize"] : [];

  return <div className="space-y-6">
    <section><p className="text-xs font-medium text-slate-400">Payroll operations</p><h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900">Payroll processing</h2><p className="mt-1 text-sm text-slate-500">Create or retrieve a run, then use the actions allowed by its persisted state.</p></section>

    <div className="grid gap-4 xl:grid-cols-2">
      <form onSubmit={createRun} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex items-center gap-2"><Play size={16} className="text-blue-700" /><h3 className="text-sm font-semibold text-slate-900">Create payroll run</h3></div>
        <p className="mt-1 text-xs text-slate-500">Creates a run in CREATED state. The backend enforces the period's uniqueness and permission.</p>
        <div className="mt-4 grid grid-cols-2 gap-3"><label className="text-xs font-semibold text-slate-600">Year<input className={input} type="number" min="1" max="65535" step="1" required value={year} onChange={(event) => setYear(event.target.value)} /></label><label className="text-xs font-semibold text-slate-600">Month<input className={input} type="number" min="1" max="12" step="1" required value={month} onChange={(event) => setMonth(event.target.value)} /></label></div>
        <button disabled={runBusy || Boolean(activeAction)} className="mt-4 h-10 rounded-lg bg-blue-700 px-4 text-sm font-semibold text-white hover:bg-blue-800 disabled:opacity-50">{runBusy ? "Working…" : "Create run"}</button>
      </form>
      <form onSubmit={retrieveRun} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex items-center gap-2"><Activity size={16} className="text-blue-700" /><h3 className="text-sm font-semibold text-slate-900">Retrieve a payroll run</h3></div>
        <p className="mt-1 text-xs text-slate-500">The API has no run-list endpoint. Enter a run ID to retrieve its current persisted status.</p>
        <label className="mt-4 block text-xs font-semibold text-slate-600">Payroll Run ID<input className={input} type="number" min="1" step="1" required value={lookupId} onChange={(event) => setLookupId(event.target.value)} placeholder="Run ID" /></label>
        <div className="mt-4 flex gap-2"><button disabled={runBusy || Boolean(activeAction)} className="h-10 rounded-lg border border-slate-200 px-4 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50">{runBusy ? "Loading…" : "Retrieve"}</button>{run && <button type="button" disabled={runBusy} onClick={() => void refreshRun(run.payroll_run_id).catch(() => undefined)} className="inline-flex h-10 items-center gap-2 rounded-lg px-3 text-sm font-semibold text-blue-700 hover:bg-blue-50"><RefreshCw size={14} />Refresh</button>}</div>
      </form>
    </div>

    {runError && <div role="alert" className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{runError}</div>}
    {notice && <div role="status" className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">{notice}</div>}

    {run && <section className="space-y-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start"><div><p className="text-xs font-medium text-slate-400">Payroll Run {run.payroll_run_id}</p><h3 className="mt-1 text-xl font-semibold text-slate-900">{run.payroll_year}-{String(run.payroll_month).padStart(2, "0")}</h3><p className="mt-1 text-xs text-slate-500">Initiated by user {run.initiated_by_user_id}</p></div><span className={`w-fit rounded-full px-3 py-1 text-xs font-bold ${statusStyles[run.status]}`}>{run.status}</span></div>
      {runBusy && <p role="status" className="text-xs text-slate-500">Refreshing run status…</p>}
      {run.status === "PROCESSING" && <p className="rounded-lg bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-900">The backend does not expose lease expiry in the run response. Recovery can be requested here; the server will reject it unless the active attempt lease has expired.</p>}
      {actions.length > 0 && <div className="flex flex-wrap gap-2">{actions.map((action) => <button key={action} type="button" disabled={Boolean(activeAction) || runBusy} onClick={() => void performAction(action)} className={`inline-flex h-10 items-center gap-2 rounded-lg px-4 text-sm font-semibold disabled:opacity-50 ${action === "finalize" ? "bg-emerald-700 text-white hover:bg-emerald-800" : action === "retry" || action === "recover" ? "border border-amber-200 bg-amber-50 text-amber-900 hover:bg-amber-100" : "bg-blue-700 text-white hover:bg-blue-800"}`}>
        {action === "finalize" ? <CheckCircle2 size={15} /> : action === "retry" || action === "recover" ? <RotateCcw size={15} /> : <Play size={15} />}{activeAction === action ? "Submitting…" : actionLabels[action]}
      </button>)}</div>}
      {run.status === "FAILED" && <p className="rounded-lg bg-rose-50 px-3 py-2 text-xs leading-5 text-rose-800">This run failed. Retry is available through the controlled backend transition. Run diagnostics are not exposed by the current run retrieval response.</p>}
      {run.status === "PROCESSED" && <p className="text-xs text-slate-500">Processing completed. Finalization rechecks blocking issues and other prerequisites on the server.</p>}
      {run.status === "FINALIZED" && <div className="space-y-4 border-t border-slate-100 pt-4">
        <div className="flex items-center gap-2"><FileText size={16} className="text-emerald-700" /><h4 className="text-sm font-semibold text-slate-900">Finalized payroll reports</h4></div>
        <div role="tablist" aria-label="Finalized payroll reports" className="flex flex-wrap gap-2">{(["summary", "results", "components"] as const).map((item) => <button key={item} type="button" role="tab" aria-selected={tab === item} onClick={() => chooseTab(item)} className={`rounded-lg px-3 py-2 text-xs font-semibold capitalize ${tab === item ? "bg-blue-50 text-blue-700" : "text-slate-500 hover:bg-slate-50"}`}>{item === "results" ? "Employee results" : item === "components" ? "Component breakdown" : item}</button>)}</div>
        {report.kind === "loading" && <div role="status" className="rounded-lg bg-slate-50 p-6 text-center text-sm text-slate-500">Loading persisted report data…</div>}
        {report.kind === "error" && <div role="alert" className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800"><p>{report.message}</p><p className="mt-1 text-xs">Report access is controlled by persisted report.payroll.read permission.</p><button type="button" onClick={() => setReportReload((value) => value + 1)} className="mt-2 font-semibold underline">Retry</button></div>}
        {report.kind === "summary" && <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"><Metric label="Employee results" value={report.data.employee_result_count} /><Metric label="Gross pay" value={money(report.data.total_gross_pay)} /><Metric label="Deductions" value={money(report.data.total_deductions)} /><Metric label="Net pay" value={money(report.data.total_net_pay)} /></div>}
        {report.kind === "results" && <>
          {report.data.results.length === 0 ? <EmptyReport text="No persisted employee results are available for this run." /> : <div className="overflow-x-auto rounded-lg border border-slate-200"><table className="w-full min-w-[980px] text-left text-sm"><thead className="bg-slate-50 text-[11px] uppercase tracking-wide text-slate-500"><tr>{["Employee", "Result", "Assignment", "Gross", "Deductions", "Net", "Payslip record"].map((label) => <th key={label} className="px-4 py-3 font-semibold">{label}</th>)}</tr></thead><tbody className="divide-y divide-slate-100">{report.data.results.map((row) => <tr key={row.payroll_result_id}><td className="px-4 py-3 text-slate-700">{row.employee_name ?? `Employee ${row.employee_id}`}<p className="text-xs text-slate-400">{row.employee_code ?? "Code unavailable"} · ID {row.employee_id}</p></td><td className="px-4 py-3">{row.payroll_result_id}</td><td className="px-4 py-3">{row.salary_assignment_id}</td><td className="px-4 py-3">{money(row.gross_earnings)}</td><td className="px-4 py-3">{money(row.total_deductions)}</td><td className="px-4 py-3 font-semibold">{money(row.net_salary)}</td><td className="px-4 py-3">{payslips[row.payroll_result_id]?.response ? <div role="status" className="max-w-64 text-xs text-emerald-800">Created payslip {payslips[row.payroll_result_id].response?.payslip_number}<p className="mt-1 text-slate-500">ID {payslips[row.payroll_result_id].response?.payslip_id} · {payslips[row.payroll_result_id].response?.generated_at}</p><p className="mt-1 text-slate-500">No document is available (document_path is null).</p></div> : payslipTarget === row.payroll_result_id ? <form onSubmit={(event) => void generatePayslip(event, row.payroll_result_id)} className="min-w-52 space-y-2"><label className="block text-[11px] font-medium text-slate-600">Payslip number<input className={`${input} h-9`} required maxLength={50} value={payslipNumber} onChange={(event) => setPayslipNumber(event.target.value)} /></label><div className="flex gap-2"><button disabled={payslipBusyId !== null} className="rounded-md bg-blue-700 px-2.5 py-1.5 text-xs font-semibold text-white disabled:opacity-50">{payslipBusyId === row.payroll_result_id ? "Creating…" : "Confirm"}</button><button type="button" disabled={payslipBusyId !== null} onClick={() => setPayslipTarget(null)} className="px-2 py-1.5 text-xs text-slate-500">Cancel</button></div>{payslips[row.payroll_result_id]?.error && <p role="alert" className="text-xs text-rose-700">{payslips[row.payroll_result_id].error}</p>}</form> : <><button type="button" onClick={() => { setPayslipTarget(row.payroll_result_id); setPayslipNumber(""); }} className="text-xs font-semibold text-blue-700 hover:underline">Create record</button>{payslips[row.payroll_result_id]?.error && <p role="alert" className="mt-1 max-w-52 text-xs text-rose-700">{payslips[row.payroll_result_id].error}</p>}</>}</td></tr>)}</tbody></table></div>}
          <ReportPagination page={page} pagination={report.data.pagination} onPrevious={previousPage} onNext={() => nextPage(report.data.pagination.has_more, report.data.pagination.next_cursor)} />
        </>}
        {report.kind === "components" && <>
          <form onSubmit={applyComponentFilters} className="grid gap-3 rounded-lg border border-slate-200 bg-slate-50 p-3 sm:grid-cols-2 xl:grid-cols-4" aria-label="Payroll component report filters"><label className="text-xs font-semibold text-slate-600">Employee ID<input className={input} type="number" min="1" step="1" value={componentFilterDraft.employee_id} onChange={(event) => setComponentFilterDraft({ ...componentFilterDraft, employee_id: event.target.value })} /></label><label className="text-xs font-semibold text-slate-600">Salary component ID<input className={input} type="number" min="1" step="1" value={componentFilterDraft.salary_component_id} onChange={(event) => setComponentFilterDraft({ ...componentFilterDraft, salary_component_id: event.target.value })} /></label><label className="text-xs font-semibold text-slate-600">Component type<select className={input} value={componentFilterDraft.component_type} onChange={(event) => setComponentFilterDraft({ ...componentFilterDraft, component_type: event.target.value as ComponentFilters["component_type"] })}><option value="">All types</option><option value="EARNING">EARNING</option><option value="DEDUCTION">DEDUCTION</option></select></label><div className="flex items-end gap-2"><button className="h-10 flex-1 rounded-lg bg-blue-700 px-3 text-xs font-semibold text-white">Apply filters</button><button type="button" onClick={() => { setComponentFilterDraft(emptyComponentFilters); setComponentFilters(emptyComponentFilters); setComponentFilterError(null); setCursor(null); setCursorHistory([null]); setPage(1); }} className="h-10 px-2 text-xs text-slate-500">Clear</button></div>{componentFilterError && <p role="alert" className="text-xs text-rose-700 sm:col-span-2 xl:col-span-4">{componentFilterError}</p>}</form>
          {report.data.components.length === 0 ? <EmptyReport text="No persisted component rows are available for this run." /> : <div className="overflow-x-auto rounded-lg border border-slate-200"><table className="w-full min-w-[850px] text-left text-sm"><thead className="bg-slate-50 text-[11px] uppercase tracking-wide text-slate-500"><tr>{["Employee", "Component", "Type", "Amount", "Order", "Result"].map((label) => <th key={label} className="px-4 py-3 font-semibold">{label}</th>)}</tr></thead><tbody className="divide-y divide-slate-100">{report.data.components.map((row) => <tr key={row.payroll_result_component_id}><td className="px-4 py-3">{row.employee_name ?? `Employee ${row.employee_id}`}<p className="text-xs text-slate-400">{row.employee_code ?? "Code unavailable"}</p></td><td className="px-4 py-3">{row.component_name}<p className="text-xs text-slate-400">{row.component_code} · ID {row.salary_component_id}</p></td><td className="px-4 py-3">{row.component_type}</td><td className="px-4 py-3 font-semibold">{money(row.amount)}</td><td className="px-4 py-3">{row.calculation_order}</td><td className="px-4 py-3">{row.payroll_result_id}</td></tr>)}</tbody></table></div>}
          <ReportPagination page={page} pagination={report.data.pagination} onPrevious={previousPage} onNext={() => nextPage(report.data.pagination.has_more, report.data.pagination.next_cursor)} />
        </>}
        <p className="text-xs text-slate-400">Financial values are displayed from persisted finalized report responses; this page performs no payroll calculations. Payslip creation uses the database-record endpoint and requires payroll.payslip.create. The backend has no payslip retrieval or download endpoint, and this action does not create a PDF or document.</p>
      </div>}
      {run.status !== "FINALIZED" && <p className="border-t border-slate-100 pt-4 text-xs text-slate-400">Payroll results and payslips are not exposed before finalization.</p>}
    </section>}

    <div className="flex items-start gap-2 rounded-lg border border-blue-100 bg-blue-50/60 px-4 py-3 text-xs leading-5 text-blue-900"><ShieldAlert size={15} className="mt-0.5 shrink-0" /><p>Actions are submitted to the backend, which enforces persisted permissions, run state, attempt fencing, and finalization prerequisites. This screen does not infer permissions from role names or calculate payroll.</p></div>
  </div>;
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return <article className="rounded-lg border border-slate-200 bg-slate-50 p-4"><p className="text-xs font-medium text-slate-500">{label}</p><p className="mt-2 break-all text-lg font-semibold text-slate-900">{value}</p></article>;
}

function EmptyReport({ text }: { text: string }) { return <div className="rounded-lg border border-dashed border-slate-300 px-5 py-8 text-center text-sm text-slate-500">{text}</div>; }

function ReportPagination({ page, pagination, onPrevious, onNext }: { page: number; pagination: { limit: number; has_more: boolean; next_cursor: string | null }; onPrevious: () => void; onNext: () => void }) {
  return <CursorPager page={page} limit={pagination.limit} hasMore={pagination.has_more} onPrevious={onPrevious} onNext={onNext} />;
}
