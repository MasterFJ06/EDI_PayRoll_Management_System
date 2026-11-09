import { useEffect, useState } from "react";
import { Receipt, ShieldAlert, FileText, CheckCircle2 } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { FilterBar } from "@/components/common/FilterBar";
import { SearchBar } from "@/components/common/SearchBar";
import { Select } from "@/components/ui/Select";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Card, CardContent } from "@/components/ui/Card";
import { DataTable, type Column } from "@/components/tables/DataTable";
import { ErrorState } from "@/components/common/ErrorState";
import { listDeductions, listTaxRules } from "@/services/deductionService";
import { listEmployees } from "@/services/employeeService";
import { formatDate, formatINR } from "@/utils/format";
import type { Deduction, DeductionType, TaxRule, Employee } from "@/types";

const RULE_INFO: { type: DeductionType; description: string }[] = [
  { type: "PF", description: "12% of Basic Salary, matched by employer contribution." },
  { type: "ESI", description: "0.75% of gross salary for employees earning \u2264 \u20b921,000/month." },
  { type: "Professional Tax", description: "Maharashtra state PT slab, flat monthly deduction." },
  { type: "Income Tax", description: "Computed under the new tax regime slabs for FY 2026\u201327." },
];

export default function Deductions() {
  const [items, setItems] = useState<Deduction[]>([]);
  const [employeesList, setEmployeesList] = useState<Employee[]>([]);
  const [taxRules, setTaxRules] = useState<TaxRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [employeeFilter, setEmployeeFilter] = useState("all");

  async function load() {
    setLoading(true);
    setError(false);
    try {
      const [deds, emps, rules] = await Promise.all([
        listDeductions(),
        listEmployees().catch(() => [] as Employee[]),
        listTaxRules().catch(() => [] as TaxRule[]),
      ]);
      setItems(deds);
      setEmployeesList(emps);
      setTaxRules(rules);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  function findEmployee(id: string): Employee | undefined {
    if (!id) return undefined;
    return employeesList.find((e) => e.employeeCode === id || e.id === id);
  }

  function getEmployeeName(id: string): string {
    const emp = findEmployee(id);
    if (emp) return `${emp.firstName} ${emp.lastName}`;
    return id || "Unknown";
  }

  const filtered = items.filter((d) => {
    const empName = getEmployeeName(d.employeeId);
    const matchSearch =
      empName.toLowerCase().includes(search.toLowerCase()) ||
      d.employeeId.toLowerCase().includes(search.toLowerCase()) ||
      d.ruleApplied.toLowerCase().includes(search.toLowerCase());
    const matchType = typeFilter === "all" || d.type === typeFilter;
    const matchEmp =
      employeeFilter === "all" ||
      d.employeeId === employeeFilter ||
      findEmployee(d.employeeId)?.id === employeeFilter;
    return matchSearch && matchType && matchEmp;
  });

  const columns: Column<Deduction>[] = [
    {
      key: "employee",
      header: "Employee",
      sortValue: (d) => getEmployeeName(d.employeeId),
      render: (d) => {
        const emp = findEmployee(d.employeeId);
        return (
          <div>
            <span className="font-medium text-text">{getEmployeeName(d.employeeId)}</span>
            {emp && emp.employeeCode !== getEmployeeName(d.employeeId) && (
              <span className="block text-xs font-mono text-text-muted">{emp.employeeCode}</span>
            )}
          </div>
        );
      },
    },
    { key: "type", header: "Deduction Type", render: (d) => d.type },
    { key: "method", header: "Calculation Method", render: (d) => d.calculationMethod },
    { key: "rule", header: "Rule Applied", render: (d) => <span className="text-text-muted">{d.ruleApplied}</span> },
    {
      key: "amount",
      header: "Amount",
      sortValue: (d) => d.amount,
      render: (d) => <span className="font-medium text-danger">-{formatINR(d.amount)}</span>,
    },
    {
      key: "effective",
      header: "Effective Date",
      sortValue: (d) => d.effectiveDate,
      render: (d) => formatDate(d.effectiveDate),
    },
    { key: "status", header: "Status", render: (d) => <StatusBadge status={d.status} /> },
  ];

  return (
    <div>
      <PageHeader
        title="Deductions & Tax Calculation"
        description="Configured deduction rules applied during payroll processing. Statutory rates are supplied by the FastAPI /tax-rules endpoint."
        icon={<Receipt className="h-5 w-5" />}
      />

      <div className="mb-6 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {RULE_INFO.map((r) => (
          <Card key={r.type}>
            <CardContent className="py-4">
              <p className="text-sm font-semibold text-text">{r.type}</p>
              <p className="mt-1 text-xs text-text-muted">{r.description}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {taxRules.length > 0 && (
        <Card className="mb-6 border-primary-100 bg-primary-50/30">
          <CardContent className="py-4">
            <div className="flex items-center gap-2 mb-2">
              <ShieldAlert className="h-4 w-4 text-primary" />
              <p className="text-xs font-semibold uppercase tracking-wide text-primary">
                Statutory Tax Rules (FastAPI /tax-rules)
              </p>
            </div>
            <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-3">
              {taxRules.map((tr) => (
                <div key={tr.id} className="rounded border border-border/80 bg-white p-3 text-xs shadow-2xs">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-text">{tr.rule_name}</span>
                    <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium text-slate-600">
                      {tr.regime}
                    </span>
                  </div>
                  <p className="mt-1 text-text-muted">{tr.slab_details}</p>
                  <p className="mt-1 text-[10px] text-text-muted/70">{tr.applicable_year}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <FilterBar>
        <SearchBar
          value={search}
          onChange={setSearch}
          placeholder="Search employee or rule"
          className="w-full sm:w-64"
        />
        <Select
          value={employeeFilter}
          onChange={(e) => setEmployeeFilter(e.target.value)}
          className="w-full sm:w-48"
        >
          <option value="all">All Employees</option>
          {employeesList.map((emp) => (
            <option key={emp.id} value={emp.employeeCode || emp.id}>
              {emp.firstName} {emp.lastName} ({emp.employeeCode})
            </option>
          ))}
        </Select>
        <Select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="w-full sm:w-48"
        >
          <option value="all">All Deduction Types</option>
          <option>PF</option>
          <option>ESI</option>
          <option>Professional Tax</option>
          <option>Income Tax</option>
          <option>Insurance</option>
          <option>Loan</option>
          <option>Other</option>
        </Select>
      </FilterBar>

      <div className="mt-4">
        {error ? (
          <ErrorState onRetry={load} />
        ) : (
          <DataTable
            columns={columns}
            data={filtered}
            rowKey={(d) => d.id}
            loading={loading}
            pageSize={8}
            emptyTitle="No deductions found"
          />
        )}
      </div>
    </div>
  );
}
