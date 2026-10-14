import { useState, type FormEvent } from "react";
import { ArrowLeft, UserPlus } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { ApiError, apiClient, type EmployeeCreateRequest, type EmployeeCreateResponse } from "../api/client";

const fieldClass = "mt-1.5 h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-800 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10";
type FormValues = { employee_code: string; first_name: string; last_name: string; department_id: string; designation_id: string; user_id: string; manager_employee_id: string; joining_date: string; employment_end_date: string };
const initial: FormValues = { employee_code: "", first_name: "", last_name: "", department_id: "", designation_id: "", user_id: "", manager_employee_id: "", joining_date: "", employment_end_date: "" };

function positiveId(value: string): number | undefined { return value ? Number(value) : undefined; }

export function CreateEmployeePage() {
  const navigate = useNavigate();
  const [values, setValues] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (!values.employee_code.trim() || !values.first_name.trim() || !values.last_name.trim()) {
      setError("Employee code, first name, and last name cannot be blank.");
      return;
    }
    if (values.employment_end_date && values.employment_end_date < values.joining_date) {
      setError("Employment end date cannot be before joining date.");
      return;
    }
    const request: EmployeeCreateRequest = {
      employee_code: values.employee_code.trim(),
      first_name: values.first_name.trim(),
      last_name: values.last_name.trim(),
      department_id: Number(values.department_id),
      designation_id: Number(values.designation_id),
      joining_date: values.joining_date,
      ...(positiveId(values.user_id) ? { user_id: positiveId(values.user_id) } : {}),
      ...(positiveId(values.manager_employee_id) ? { manager_employee_id: positiveId(values.manager_employee_id) } : {}),
      ...(values.employment_end_date ? { employment_end_date: values.employment_end_date } : {}),
    };
    setBusy(true);
    try {
      const employee = await apiClient.post<EmployeeCreateResponse>("/employees", request);
      navigate(`/employees/${encodeURIComponent(employee.employee_code)}`, { replace: true, state: { createdEmployee: employee } });
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 403) setError("Your account is not authorized to create employees.");
      else setError(caught instanceof ApiError ? caught.message : "Employee creation failed. Check the API connection and try again.");
    } finally {
      setBusy(false);
    }
  }

  function update<K extends keyof FormValues>(key: K, value: FormValues[K]) { setValues((current) => ({ ...current, [key]: value })); }
  const required = <span className="text-rose-600" aria-hidden="true"> *</span>;
  return <div className="mx-auto max-w-3xl space-y-5">
    <Link to="/employees" className="inline-flex items-center gap-2 text-sm font-semibold text-slate-500 hover:text-blue-700"><ArrowLeft size={16} />Employee directory</Link>
    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
      <div className="mb-6 flex items-start gap-3"><div className="grid size-10 place-items-center rounded-lg bg-blue-50 text-blue-700"><UserPlus size={18} /></div><div><p className="text-xs font-medium text-slate-400">Employee Management</p><h2 className="mt-1 text-xl font-semibold text-slate-900">Add employee</h2><p className="mt-1 text-sm text-slate-500">Create a record using the existing employee API.</p></div></div>
      <p className="mb-5 rounded-lg border border-blue-100 bg-blue-50/70 px-4 py-3 text-xs leading-5 text-blue-900">Department and designation lookup endpoints are not available. Enter IDs for existing records. Optional user and manager IDs must also refer to existing records.</p>
      <form onSubmit={submit} className="space-y-5">
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="text-xs font-semibold text-slate-600">Employee code{required}<input className={fieldClass} required minLength={1} maxLength={30} value={values.employee_code} onChange={(e) => update("employee_code", e.target.value)} /></label>
          <label className="text-xs font-semibold text-slate-600">First name{required}<input className={fieldClass} required minLength={1} maxLength={100} autoComplete="given-name" value={values.first_name} onChange={(e) => update("first_name", e.target.value)} /></label>
          <label className="text-xs font-semibold text-slate-600">Last name{required}<input className={fieldClass} required minLength={1} maxLength={100} autoComplete="family-name" value={values.last_name} onChange={(e) => update("last_name", e.target.value)} /></label>
          <label className="text-xs font-semibold text-slate-600">Department ID{required}<input className={fieldClass} required type="number" min="1" step="1" value={values.department_id} onChange={(e) => update("department_id", e.target.value)} /></label>
          <label className="text-xs font-semibold text-slate-600">Designation ID{required}<input className={fieldClass} required type="number" min="1" step="1" value={values.designation_id} onChange={(e) => update("designation_id", e.target.value)} /></label>
          <label className="text-xs font-semibold text-slate-600">Linked user ID <span className="font-normal text-slate-400">(optional)</span><input className={fieldClass} type="number" min="1" step="1" value={values.user_id} onChange={(e) => update("user_id", e.target.value)} /></label>
          <label className="text-xs font-semibold text-slate-600">Manager employee ID <span className="font-normal text-slate-400">(optional)</span><input className={fieldClass} type="number" min="1" step="1" value={values.manager_employee_id} onChange={(e) => update("manager_employee_id", e.target.value)} /></label>
          <label className="text-xs font-semibold text-slate-600">Joining date{required}<input className={fieldClass} required type="date" value={values.joining_date} onChange={(e) => update("joining_date", e.target.value)} /></label>
          <label className="text-xs font-semibold text-slate-600">Employment end date <span className="font-normal text-slate-400">(optional)</span><input className={fieldClass} type="date" min={values.joining_date || undefined} value={values.employment_end_date} onChange={(e) => update("employment_end_date", e.target.value)} /></label>
        </div>
        {error && <div role="alert" className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{error}</div>}
        <div className="flex flex-col-reverse justify-end gap-2 border-t border-slate-100 pt-5 sm:flex-row"><Link to="/employees" className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 px-4 text-sm font-semibold text-slate-600 hover:bg-slate-50">Cancel</Link><button disabled={busy} type="submit" className="inline-flex h-10 items-center justify-center rounded-lg bg-blue-700 px-5 text-sm font-semibold text-white hover:bg-blue-800 disabled:cursor-wait disabled:opacity-60">{busy ? "Creating…" : "Create employee"}</button></div>
      </form>
    </section>
  </div>;
}
