import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Wallet, Plus, Eye } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { FilterBar } from "@/components/common/FilterBar";
import { SearchBar } from "@/components/common/SearchBar";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Select } from "@/components/ui/Select";
import { Dialog } from "@/components/ui/Dialog";
import { StatusBadge } from "@/components/common/StatusBadge";
import { DataTable, type Column } from "@/components/tables/DataTable";
import { ErrorState } from "@/components/common/ErrorState";
import { listSalaryStructures, createSalaryStructure, computeGross, computeDeductions } from "@/services/salaryService";
import { employees, employeeName } from "@/data/mockData";
import { formatDate, formatINR } from "@/utils/format";
import type { SalaryStructure } from "@/types";

const schema = z.object({
  employeeId: z.string().min(1, "Employee is required"),
  basic: z.coerce.number().min(0, "Basic salary cannot be negative"),
  hra: z.coerce.number().min(0),
  da: z.coerce.number().min(0),
  specialAllowance: z.coerce.number().min(0),
  travelAllowance: z.coerce.number().min(0),
  medicalAllowance: z.coerce.number().min(0),
  otherAllowances: z.coerce.number().min(0),
  providentFund: z.coerce.number().min(0),
  professionalTax: z.coerce.number().min(0),
  incomeTax: z.coerce.number().min(0),
  insurance: z.coerce.number().min(0),
  esi: z.coerce.number().min(0),
  bonus: z.coerce.number().min(0),
  loanDeduction: z.coerce.number().min(0),
  otherDeductions: z.coerce.number().min(0),
  effectiveFrom: z.string().min(1, "Effective from date is required"),
});
type FormValues = z.infer<typeof schema>;

export default function SalaryStructures() {
  const [items, setItems] = useState<SalaryStructure[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [search, setSearch] = useState("");
  const [formOpen, setFormOpen] = useState(false);
  const [viewing, setViewing] = useState<SalaryStructure | null>(null);

  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { basic: 0, hra: 0, da: 0, specialAllowance: 0, travelAllowance: 0, medicalAllowance: 0, otherAllowances: 0, providentFund: 0, professionalTax: 0, incomeTax: 0, insurance: 0, esi: 0, bonus: 0, loanDeduction: 0, otherDeductions: 0 },
  });

  async function load() {
    setLoading(true); setError(false);
    try { setItems(await listSalaryStructures()); } catch { setError(true); } finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []);

  const filtered = items.filter((s) => employeeName(s.employeeId).toLowerCase().includes(search.toLowerCase()));

  async function onSubmit(values: FormValues) {
    await createSalaryStructure({
      id: `SS-${values.employeeId}-${Date.now()}`, ...values, overtimeRate: 350,
      effectiveTo: null, revisionNumber: 1, status: "Active",
    });
    setFormOpen(false);
    reset();
    load();
  }

  const columns: Column<SalaryStructure>[] = [
    { key: "employee", header: "Employee", sortValue: (s) => employeeName(s.employeeId), render: (s) => <span className="font-medium text-text">{employeeName(s.employeeId)}</span> },
    { key: "basic", header: "Basic Salary", sortValue: (s) => s.basic, render: (s) => formatINR(s.basic) },
    { key: "gross", header: "Gross Salary", sortValue: (s) => computeGross(s), render: (s) => <span className="font-medium text-text">{formatINR(computeGross(s))}</span> },
    { key: "deductions", header: "Total Deductions", sortValue: (s) => computeDeductions(s), render: (s) => <span className="text-danger">-{formatINR(computeDeductions(s))}</span> },
    { key: "net", header: "Net Salary", sortValue: (s) => computeGross(s) - computeDeductions(s), render: (s) => <span className="font-semibold text-success">{formatINR(computeGross(s) - computeDeductions(s))}</span> },
    { key: "effective", header: "Effective From", sortValue: (s) => s.effectiveFrom, render: (s) => formatDate(s.effectiveFrom) },
    { key: "status", header: "Status", render: (s) => <StatusBadge status={s.status} /> },
    { key: "actions", header: "", render: (s) => <Button variant="ghost" size="icon" onClick={() => setViewing(s)} aria-label="View breakdown"><Eye className="h-4 w-4" /></Button> },
  ];

  return (
    <div>
      <PageHeader
        title="Salary Structure Management"
        description="Configure earnings and deduction components per employee. Statutory rates are sourced from the FastAPI /tax-rules endpoint."
        icon={<Wallet className="h-5 w-5" />}
        actions={<Button onClick={() => setFormOpen(true)}><Plus className="h-4 w-4" /> New Structure</Button>}
      />

      <FilterBar>
        <SearchBar value={search} onChange={setSearch} placeholder="Search by employee" className="w-full sm:w-72" />
      </FilterBar>

      <div className="mt-4">
        {error ? <ErrorState onRetry={load} /> : (
          <DataTable columns={columns} data={filtered} rowKey={(s) => s.id} loading={loading} pageSize={8} emptyTitle="No salary structures found" />
        )}
      </div>

      <Dialog
        open={formOpen} onClose={() => setFormOpen(false)} title="New Salary Structure" size="lg"
        description="Gross = Basic + HRA + DA + Allowances + Bonus + Overtime. Net = Gross \u2212 Total Deductions."
        footer={<>
          <Button variant="outline" onClick={() => setFormOpen(false)}>Cancel</Button>
          <Button onClick={handleSubmit(onSubmit)} loading={isSubmitting}>Save Structure</Button>
        </>}
      >
        <form className="grid grid-cols-1 gap-4 sm:grid-cols-2" onSubmit={handleSubmit(onSubmit)}>
          <div className="sm:col-span-2">
            <Label required>Employee</Label>
            <Select {...register("employeeId")} error={!!errors.employeeId}>
              <option value="">Select employee</option>
              {employees.map((e) => <option key={e.id} value={e.id}>{e.firstName} {e.lastName} ({e.employeeCode})</option>)}
            </Select>
            {errors.employeeId && <p className="mt-1 text-xs text-danger">{errors.employeeId.message}</p>}
          </div>
          <div><Label required>Basic Salary (\u20b9)</Label><Input type="number" {...register("basic")} error={!!errors.basic} />{errors.basic && <p className="mt-1 text-xs text-danger">{errors.basic.message}</p>}</div>
          <div><Label required>HRA (\u20b9)</Label><Input type="number" {...register("hra")} /></div>
          <div><Label required>DA (\u20b9)</Label><Input type="number" {...register("da")} /></div>
          <div><Label>Special Allowance (\u20b9)</Label><Input type="number" {...register("specialAllowance")} /></div>
          <div><Label>Travel Allowance (\u20b9)</Label><Input type="number" {...register("travelAllowance")} /></div>
          <div><Label>Medical Allowance (\u20b9)</Label><Input type="number" {...register("medicalAllowance")} /></div>
          <div><Label>Other Allowances (\u20b9)</Label><Input type="number" {...register("otherAllowances")} /></div>
          <div><Label required>Provident Fund (\u20b9)</Label><Input type="number" {...register("providentFund")} /></div>
          <div><Label required>Professional Tax (\u20b9)</Label><Input type="number" {...register("professionalTax")} /></div>
          <div><Label required>Income Tax (\u20b9)</Label><Input type="number" {...register("incomeTax")} /></div>
          <div><Label>Insurance (\u20b9)</Label><Input type="number" {...register("insurance")} /></div>
          <div><Label required>Effective From</Label><Input type="date" {...register("effectiveFrom")} error={!!errors.effectiveFrom} /></div>
        </form>
      </Dialog>

      <Dialog open={!!viewing} onClose={() => setViewing(null)} title="Salary Breakdown" size="sm">
        {viewing && (
          <div className="space-y-1 text-sm">
            <p className="mb-2 font-medium text-text">{employeeName(viewing.employeeId)}</p>
            {[
              ["Basic", viewing.basic], ["HRA", viewing.hra], ["DA", viewing.da], ["Special Allowance", viewing.specialAllowance],
              ["Travel Allowance", viewing.travelAllowance], ["Medical Allowance", viewing.medicalAllowance], ["Other Allowances", viewing.otherAllowances],
            ].map(([label, val]) => (
              <div key={label as string} className="flex justify-between border-b border-border py-1.5"><span className="text-text-muted">{label}</span><span className="text-text">{formatINR(val as number)}</span></div>
            ))}
            <div className="flex justify-between py-1.5 font-medium"><span>Gross Salary</span><span>{formatINR(computeGross(viewing))}</span></div>
            {[
              ["PF", viewing.providentFund], ["ESI", viewing.esi], ["Professional Tax", viewing.professionalTax],
              ["Income Tax", viewing.incomeTax], ["Insurance", viewing.insurance], ["Loan", viewing.loanDeduction], ["Other Deductions", viewing.otherDeductions],
            ].map(([label, val]) => (
              <div key={label as string} className="flex justify-between border-b border-border py-1.5"><span className="text-text-muted">{label}</span><span className="text-danger">-{formatINR(val as number)}</span></div>
            ))}
            <div className="flex justify-between pt-2 text-base font-semibold"><span>Net Salary</span><span className="text-success">{formatINR(computeGross(viewing) - computeDeductions(viewing))}</span></div>
          </div>
        )}
      </Dialog>
    </div>
  );
}
