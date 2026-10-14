import { useState, type FormEvent, type ReactNode } from "react";
import { ArrowLeft, CalendarRange, CircleDollarSign, Layers3, Link2, Plus, Shapes } from "lucide-react";
import { ApiError, apiClient, type CompensationStatus, type SalaryComponentType, type CalculationType, type SalaryStructureCreateRequest, type SalaryStructureResponse, type SalaryComponentCreateRequest, type SalaryComponentResponse, type SalaryRevisionCreateRequest, type SalaryRevisionResponse, type SalaryRevisionComponentCreateRequest, type SalaryRevisionComponentResponse, type EmployeeSalaryAssignmentCreateRequest, type EmployeeSalaryAssignmentResponse } from "../api/client";

type Workflow = "structure" | "component" | "revision" | "revision-component" | "assignment";
const input = "mt-1.5 h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-800 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10";
const select = input;

const workflows: { id: Workflow; title: string; description: string; icon: typeof Shapes; endpoint: string }[] = [
  { id: "structure", title: "Salary structures", description: "Create a named salary structure.", icon: Layers3, endpoint: "POST /api/v1/salary-structures" },
  { id: "component", title: "Salary components", description: "Create an earning or deduction definition.", icon: Shapes, endpoint: "POST /api/v1/salary-components" },
  { id: "revision", title: "Salary revisions", description: "Create an effective-dated structure revision.", icon: CalendarRange, endpoint: "POST /api/v1/salary-revisions" },
  { id: "revision-component", title: "Revision components", description: "Configure fixed or percentage components for a revision.", icon: CircleDollarSign, endpoint: "POST /api/v1/salary-revision-components" },
  { id: "assignment", title: "Employee assignments", description: "Assign a revision to an employee for an effective period.", icon: Link2, endpoint: "POST /api/v1/employee-salary-assignments" },
];

function FormFrame({ title, subtitle, note, onBack, busy, error, children, onSubmit }: { title: string; subtitle: string; note: string; onBack: () => void; busy: boolean; error: string | null; children: ReactNode; onSubmit: (event: FormEvent<HTMLFormElement>) => void }) {
  return <section className="mx-auto max-w-3xl rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
    <button type="button" onClick={onBack} className="mb-5 inline-flex items-center gap-2 text-sm font-semibold text-slate-500 hover:text-blue-700"><ArrowLeft size={15} />Compensation</button>
    <p className="text-xs font-medium text-slate-400">Compensation Management</p><h2 className="mt-1 text-xl font-semibold text-slate-900">{title}</h2><p className="mt-1 text-sm text-slate-500">{subtitle}</p>
    <p className="my-5 rounded-lg border border-blue-100 bg-blue-50/60 px-4 py-3 text-xs leading-5 text-blue-900">{note}</p>
    <form className="space-y-4" onSubmit={onSubmit}>{children}{error && <div role="alert" className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{error}</div>}<button disabled={busy} className="inline-flex h-10 w-full items-center justify-center rounded-lg bg-blue-700 px-5 text-sm font-semibold text-white hover:bg-blue-800 disabled:cursor-wait disabled:opacity-60">{busy ? "Saving…" : "Create"}</button></form>
  </section>;
}

function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: string }) { return <label className="block text-xs font-semibold text-slate-600">{label}{children}{hint && <span className="mt-1 block text-[11px] font-normal text-slate-400">{hint}</span>}</label>; }
function TextInput({ className, ...props }: React.InputHTMLAttributes<HTMLInputElement>) { return <input className={`${input} ${className ?? ""}`} {...props} />; }
function Select({ children, ...props }: React.SelectHTMLAttributes<HTMLSelectElement>) { return <select className={select} {...props}>{children}</select>; }
function ResultPanel({ result }: { result: unknown }) { return <div role="status" className="rounded-xl border border-emerald-200 bg-emerald-50 p-5"><h3 className="text-sm font-semibold text-emerald-900">Created successfully</h3><pre className="mt-3 overflow-x-auto rounded-lg bg-white/80 p-3 text-xs leading-5 text-emerald-950">{JSON.stringify(result, null, 2)}</pre></div>; }
function getError(error: unknown): string { return error instanceof ApiError && error.status === 403 ? "Your account does not have the persisted compensation.write permission." : error instanceof Error ? error.message : "The request could not be completed. Check the API connection and try again."; }
function useSubmit<T>(submitRequest: (event: FormEvent<HTMLFormElement>) => Promise<T>) {
  const [busy, setBusy] = useState(false); const [error, setError] = useState<string | null>(null); const [result, setResult] = useState<T | null>(null);
  async function onSubmit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); setError(null); setBusy(true); try { setResult(await submitRequest(event)); } catch (caught) { setError(getError(caught)); } finally { setBusy(false); } }
  return { busy, error, result, onSubmit };
}

export function CompensationPage() {
  const [workflow, setWorkflow] = useState<Workflow | null>(null);
  const back = () => setWorkflow(null);
  if (workflow === "structure") return <StructureForm onBack={back} />;
  if (workflow === "component") return <ComponentForm onBack={back} />;
  if (workflow === "revision") return <RevisionForm onBack={back} />;
  if (workflow === "revision-component") return <RevisionComponentForm onBack={back} />;
  if (workflow === "assignment") return <AssignmentForm onBack={back} />;
  return <div className="space-y-6">
    <section><p className="text-xs font-medium text-slate-400">People operations</p><h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900">Compensation</h2><p className="mt-1 text-sm text-slate-500">Create salary definitions, revisions, component configurations, and employee assignments.</p></section>
    <div role="note" className="rounded-lg border border-blue-100 bg-blue-50/60 px-4 py-3 text-xs leading-5 text-blue-900">All five create operations require the backend’s persisted <code>compensation.write</code> permission. Compensation read/list/detail endpoints are not available, so this page does not show a directory. Use IDs returned by successful creation or from an authorized source; no records or reference options are fabricated.</div>
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{workflows.map(({ id, title, description, icon: Icon, endpoint }) => <article key={id} className="flex flex-col rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex items-start gap-3"><div className="grid size-10 shrink-0 place-items-center rounded-lg bg-blue-50 text-blue-700"><Icon size={18} /></div><div><h3 className="text-sm font-semibold text-slate-900">{title}</h3><p className="mt-1 text-xs leading-5 text-slate-500">{description}</p></div></div><p className="mt-4 text-[10px] text-slate-400">{endpoint}</p><button type="button" onClick={() => setWorkflow(id)} className="mt-4 inline-flex h-9 items-center justify-center gap-2 rounded-lg border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-50"><Plus size={14} />Create</button></article>)}</div>
  </div>;
}

function StructureForm({ onBack }: { onBack: () => void }) {
  const [code, setCode] = useState(""); const [name, setName] = useState(""); const [description, setDescription] = useState(""); const [status, setStatus] = useState<CompensationStatus>("ACTIVE");
  const submit = useSubmit<SalaryStructureResponse>(async () => { const body: SalaryStructureCreateRequest = { structure_code: code.trim(), structure_name: name.trim(), ...(description.trim() ? { description: description.trim() } : {}), status }; return apiClient.post("/salary-structures", body); });
  if (submit.result) return <div className="space-y-4"><button onClick={onBack} className="text-sm font-semibold text-blue-700">← Compensation</button><ResultPanel result={submit.result} /></div>;
  return <FormFrame title="Create salary structure" subtitle="Structure code is unique." note="The API currently creates structures only. No structure listing or editing endpoint is available." onBack={onBack} {...submit}><div className="grid gap-4 sm:grid-cols-2"><Field label="Structure code"><TextInput required minLength={1} maxLength={30} value={code} onChange={(e) => setCode(e.target.value)} /></Field><Field label="Structure name"><TextInput required minLength={1} maxLength={100} value={name} onChange={(e) => setName(e.target.value)} /></Field><Field label="Description (optional)"><TextInput maxLength={500} value={description} onChange={(e) => setDescription(e.target.value)} /></Field><Field label="Status"><Select value={status} onChange={(e) => setStatus(e.target.value as CompensationStatus)}><option value="ACTIVE">ACTIVE</option><option value="INACTIVE">INACTIVE</option></Select></Field></div></FormFrame>;
}

function ComponentForm({ onBack }: { onBack: () => void }) {
  const [code, setCode] = useState(""); const [name, setName] = useState(""); const [type, setType] = useState<SalaryComponentType | "">(""); const [status, setStatus] = useState<CompensationStatus>("ACTIVE");
  const submit = useSubmit<SalaryComponentResponse>(async () => { if (!type) throw new Error("Choose an earning or deduction type."); const body: SalaryComponentCreateRequest = { component_code: code.trim(), component_name: name.trim(), component_type: type, status }; return apiClient.post("/salary-components", body); });
  if (submit.result) return <div className="space-y-4"><button onClick={onBack} className="text-sm font-semibold text-blue-700">← Compensation</button><ResultPanel result={submit.result} /></div>;
  return <FormFrame title="Create salary component" subtitle="The component code is unique." note="This creates a component definition only. Amounts and calculation configuration are defined separately on a salary revision." onBack={onBack} {...submit}><div className="grid gap-4 sm:grid-cols-2"><Field label="Component code"><TextInput required minLength={1} maxLength={30} value={code} onChange={(e) => setCode(e.target.value)} /></Field><Field label="Component name"><TextInput required minLength={1} maxLength={100} value={name} onChange={(e) => setName(e.target.value)} /></Field><Field label="Component type"><Select required value={type} onChange={(e) => setType(e.target.value as SalaryComponentType | "")}><option value="">Choose type</option><option value="EARNING">EARNING</option><option value="DEDUCTION">DEDUCTION</option></Select></Field><Field label="Status"><Select value={status} onChange={(e) => setStatus(e.target.value as CompensationStatus)}><option value="ACTIVE">ACTIVE</option><option value="INACTIVE">INACTIVE</option></Select></Field></div></FormFrame>;
}

function RevisionForm({ onBack }: { onBack: () => void }) {
  const [structureId, setStructureId] = useState(""); const [number, setNumber] = useState(""); const [from, setFrom] = useState(""); const [to, setTo] = useState("");
  const submit = useSubmit<SalaryRevisionResponse>(async () => { if (to && to < from) throw new Error("Effective end date cannot precede effective start date."); const body: SalaryRevisionCreateRequest = { salary_structure_id: Number(structureId), revision_number: Number(number), effective_from: from, ...(to ? { effective_to: to } : {}) }; return apiClient.post("/salary-revisions", body); });
  if (submit.result) return <div className="space-y-4"><button onClick={onBack} className="text-sm font-semibold text-blue-700">← Compensation</button><ResultPanel result={submit.result} /></div>;
  return <FormFrame title="Create salary revision" subtitle="An existing salary structure is required." note="No structure lookup endpoint exists. Enter a persisted salary_structure_id. The revision/number pair must be unique; there is no revision list or edit endpoint." onBack={onBack} {...submit}><div className="grid gap-4 sm:grid-cols-2"><Field label="Salary structure ID"><TextInput required type="number" min="1" step="1" value={structureId} onChange={(e) => setStructureId(e.target.value)} /></Field><Field label="Revision number"><TextInput required type="number" min="0" max="4294967295" step="1" value={number} onChange={(e) => setNumber(e.target.value)} /></Field><Field label="Effective from"><TextInput required type="date" value={from} onChange={(e) => setFrom(e.target.value)} /></Field><Field label="Effective to (optional)"><TextInput type="date" min={from || undefined} value={to} onChange={(e) => setTo(e.target.value)} /></Field></div></FormFrame>;
}

function RevisionComponentForm({ onBack }: { onBack: () => void }) {
  const [revisionId, setRevisionId] = useState(""); const [componentId, setComponentId] = useState(""); const [type, setType] = useState<CalculationType | "">(""); const [fixed, setFixed] = useState(""); const [percentage, setPercentage] = useState(""); const [base, setBase] = useState(""); const [overtime, setOvertime] = useState<"" | "true" | "false">("");
  const submit = useSubmit<SalaryRevisionComponentResponse>(async () => {
    if (!type || overtime === "") throw new Error("Choose calculation type and explicitly select whether this is the overtime base.");
    if (type === "FIXED" && !/^\d{1,13}(\.\d{1,2})?$/.test(fixed)) throw new Error("Fixed amount is required and supports at most 13 integer digits and 2 decimal places.");
    if (type === "PERCENTAGE" && (!/^\d{1,4}(\.\d{1,4})?$/.test(percentage) || !base || Number(base) <= 0)) throw new Error("Percentage value (up to 4 integer and 4 decimal digits) and a positive base component ID are required.");
    const body: SalaryRevisionComponentCreateRequest = { salary_revision_id: Number(revisionId), salary_component_id: Number(componentId), calculation_type: type, fixed_amount: type === "FIXED" ? fixed : null, percentage_value: type === "PERCENTAGE" ? percentage : null, base_component_id: type === "PERCENTAGE" ? Number(base) : null, is_overtime_base: overtime === "true" };
    return apiClient.post("/salary-revision-components", body);
  });
  if (submit.result) return <div className="space-y-4"><button onClick={onBack} className="text-sm font-semibold text-blue-700">← Compensation</button><ResultPanel result={submit.result} /></div>;
  return <FormFrame title="Configure revision component" subtitle="Connect an existing component to a revision." note="Enter persisted revision/component IDs. The API validates fixed versus percentage fields, base dependencies, duplicate assignment, and overtime-base rules; this form does not calculate salary amounts." onBack={onBack} {...submit}><div className="grid gap-4 sm:grid-cols-2"><Field label="Salary revision ID"><TextInput required type="number" min="1" step="1" value={revisionId} onChange={(e) => setRevisionId(e.target.value)} /></Field><Field label="Salary component ID"><TextInput required type="number" min="1" step="1" value={componentId} onChange={(e) => setComponentId(e.target.value)} /></Field><Field label="Calculation type"><Select required value={type} onChange={(e) => setType(e.target.value as CalculationType | "")}><option value="">Choose type</option><option value="FIXED">FIXED</option><option value="PERCENTAGE">PERCENTAGE</option></Select></Field><Field label="Overtime base designation"><Select required value={overtime} onChange={(e) => setOvertime(e.target.value as typeof overtime)}><option value="">Choose explicitly</option><option value="true">Yes</option><option value="false">No</option></Select></Field>{type === "FIXED" && <Field label="Fixed amount"><TextInput required inputMode="decimal" value={fixed} onChange={(e) => setFixed(e.target.value)} placeholder="0.00" /></Field>}{type === "PERCENTAGE" && <><Field label="Percentage value"><TextInput required inputMode="decimal" value={percentage} onChange={(e) => setPercentage(e.target.value)} placeholder="0.0000" /></Field><Field label="Base component ID"><TextInput required type="number" min="1" step="1" value={base} onChange={(e) => setBase(e.target.value)} /></Field></>}</div></FormFrame>;
}

function AssignmentForm({ onBack }: { onBack: () => void }) {
  const [employeeId, setEmployeeId] = useState(""); const [revisionId, setRevisionId] = useState(""); const [from, setFrom] = useState(""); const [to, setTo] = useState("");
  const submit = useSubmit<EmployeeSalaryAssignmentResponse>(async () => { if (to && to < from) throw new Error("Effective end date cannot precede effective start date."); const body: EmployeeSalaryAssignmentCreateRequest = { employee_id: Number(employeeId), salary_revision_id: Number(revisionId), effective_from: from, ...(to ? { effective_to: to } : {}) }; return apiClient.post("/employee-salary-assignments", body); });
  if (submit.result) return <div className="space-y-4"><button onClick={onBack} className="text-sm font-semibold text-blue-700">← Compensation</button><ResultPanel result={submit.result} /></div>;
  return <FormFrame title="Assign compensation to employee" subtitle="Assign an existing revision to an existing employee." note="Enter persisted employee and salary revision IDs. The API defines no overlap rule and this form does not invent one. No employee or revision lookup/list endpoint is available here." onBack={onBack} {...submit}><div className="grid gap-4 sm:grid-cols-2"><Field label="Employee ID"><TextInput required type="number" min="1" step="1" value={employeeId} onChange={(e) => setEmployeeId(e.target.value)} /></Field><Field label="Salary revision ID"><TextInput required type="number" min="1" step="1" value={revisionId} onChange={(e) => setRevisionId(e.target.value)} /></Field><Field label="Effective from"><TextInput required type="date" value={from} onChange={(e) => setFrom(e.target.value)} /></Field><Field label="Effective to (optional)"><TextInput type="date" min={from || undefined} value={to} onChange={(e) => setTo(e.target.value)} /></Field></div></FormFrame>;
}
