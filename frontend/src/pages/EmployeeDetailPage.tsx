import { useEffect, useState } from "react";
import { ArrowLeft, Building2, CalendarDays, UserRound } from "lucide-react";
import { Link, useLocation, useParams } from "react-router-dom";
import { ApiError, apiClient, type EmployeeCreateResponse, type EmployeeReportPage, type EmployeeReportRow } from "../api/client";

type DetailState = { status: "loading" } | { status: "ready"; employee: EmployeeReportRow } | { status: "created-fallback"; employee: EmployeeCreateResponse } | { status: "error"; message: string };

export function EmployeeDetailPage() {
  const { employeeCode = "" } = useParams();
  const location = useLocation();
  const created = (location.state as { createdEmployee?: EmployeeCreateResponse } | null)?.createdEmployee;
  const [state, setState] = useState<DetailState>({ status: "loading" });

  useEffect(() => {
    let active = true;
    setState({ status: "loading" });
    const params = new URLSearchParams({ limit: "1", employee_code: employeeCode });
    void apiClient.get<EmployeeReportPage>(`/reports/employees?${params.toString()}`).then((page) => {
      if (!active) return;
      const employee = page.employees.find((item) => item.employee_code === employeeCode);
      setState(employee ? { status: "ready", employee } : { status: "error", message: "No employee with this code was found." });
    }).catch((error: unknown) => {
      if (!active) return;
      if (created && created.employee_code === employeeCode) {
        setState({ status: "created-fallback", employee: created });
      } else if (error instanceof ApiError && error.status === 403) {
        setState({ status: "error", message: "Your account does not have permission to read employee details." });
      } else {
        setState({ status: "error", message: error instanceof ApiError ? error.message : "Employee details could not be loaded. Check the API connection and try again." });
      }
    });
    return () => { active = false; };
  }, [employeeCode, created]);

  const employee = state.status === "ready" || state.status === "created-fallback" ? state.employee : null;
  return <div className="space-y-5">
    <Link to="/employees" className="inline-flex items-center gap-2 text-sm font-semibold text-slate-500 hover:text-blue-700"><ArrowLeft size={16} />Employee directory</Link>
    {state.status === "loading" && <div className="rounded-xl border border-slate-200 bg-white p-10 text-center text-sm text-slate-500" role="status">Loading employee details…</div>}
    {state.status === "error" && <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-800"><p className="font-semibold">Employee details unavailable</p><p className="mt-1">{state.message}</p></div>}
    {employee && <>
      {state.status === "created-fallback" && <p role="status" className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-900">Created successfully. Current organization labels could not be loaded; showing fields returned by the create endpoint.</p>}
      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start"><div className="flex items-center gap-4"><div className="grid size-12 place-items-center rounded-xl bg-blue-50 text-blue-700"><UserRound size={21} /></div><div><p className="text-xs text-slate-400">{employee.employee_code} · Employee ID {employee.employee_id}</p><h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900">{employee.first_name} {employee.last_name}</h2></div></div><span className="w-fit rounded-full bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-600">{employee.employment_status}</span></div>
        <div className="mt-7 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          <Detail label="Department" value={"department_name" in employee ? employee.department_name ?? `Department ${employee.department_id}` : `Department ${employee.department_id}`} icon={<Building2 size={16} />} />
          <Detail label="Designation" value={"designation_name" in employee ? employee.designation_name ?? `Designation ${employee.designation_id}` : `Designation ${employee.designation_id}`} icon={<Building2 size={16} />} />
          <Detail label="Joining date" value={employee.joining_date} icon={<CalendarDays size={16} />} />
          <Detail label="Employment end date" value={employee.employment_end_date ?? "Not set"} icon={<CalendarDays size={16} />} />
          <Detail label="Department ID" value={String(employee.department_id)} icon={<Building2 size={16} />} />
          <Detail label="Designation ID" value={String(employee.designation_id)} icon={<Building2 size={16} />} />
        </div>
      </section>
    </>}
  </div>;
}

function Detail({ label, value, icon }: { label: string; value: string; icon: React.ReactNode }) {
  return <div className="rounded-lg border border-slate-100 bg-slate-50/60 p-4"><p className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wide text-slate-400">{icon}{label}</p><p className="mt-2 text-sm font-medium text-slate-800">{value}</p></div>;
}
