import { useEffect, useState } from "react";
import { Receipt } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { FilterBar } from "@/components/common/FilterBar";
import { SearchBar } from "@/components/common/SearchBar";
import { Select } from "@/components/ui/Select";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Card, CardContent } from "@/components/ui/Card";
import { DataTable, type Column } from "@/components/tables/DataTable";
import { ErrorState } from "@/components/common/ErrorState";
import { listDeductions } from "@/services/deductionService";
import { employeeName } from "@/data/mockData";
import { formatDate, formatINR } from "@/utils/format";
import type { Deduction, DeductionType } from "@/types";

const RULE_INFO: { type: DeductionType; description: string }[] = [
  { type: "PF", description: "12% of Basic Salary, matched by employer contribution." },
  { type: "ESI", description: "0.75% of gross salary for employees earning \u2264 \u20b921,000/month." },
  { type: "Professional Tax", description: "Maharashtra state PT slab, flat monthly deduction." },
  { type: "Income Tax", description: "Computed under the new tax regime slabs for FY 2026\u201327." },
];

export default function Deductions() {
  const [items, setItems] = useState<Deduction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");

  async function load() {
    setLoading(true); setError(false);
    try { setItems(await listDeductions()); } catch { setError(true); } finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []);

  const filtered = items.filter((d) => {
    const matchSearch = employeeName(d.employeeId).toLowerCase().includes(search.toLowerCase());
    const matchType = typeFilter === "all" || d.type === typeFilter;
    return matchSearch && matchType;
  });

  const columns: Column<Deduction>[] = [
    { key: "employee", header: "Employee", sortValue: (d) => employeeName(d.employeeId), render: (d) => <span className="font-medium text-text">{employeeName(d.employeeId)}</span> },
    { key: "type", header: "Deduction Type", render: (d) => d.type },
    { key: "method", header: "Calculation Method", render: (d) => d.calculationMethod },
    { key: "rule", header: "Rule Applied", render: (d) => <span className="text-text-muted">{d.ruleApplied}</span> },
    { key: "amount", header: "Amount", sortValue: (d) => d.amount, render: (d) => <span className="font-medium text-danger">-{formatINR(d.amount)}</span> },
    { key: "effective", header: "Effective Date", sortValue: (d) => d.effectiveDate, render: (d) => formatDate(d.effectiveDate) },
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
          <Card key={r.type}><CardContent className="py-4">
            <p className="text-sm font-semibold text-text">{r.type}</p>
            <p className="mt-1 text-xs text-text-muted">{r.description}</p>
          </CardContent></Card>
        ))}
      </div>

      <FilterBar>
        <SearchBar value={search} onChange={setSearch} placeholder="Search by employee" className="w-full sm:w-64" />
        <Select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)} className="w-full sm:w-48">
          <option value="all">All Deduction Types</option>
          <option>PF</option><option>ESI</option><option>Professional Tax</option><option>Income Tax</option>
          <option>Insurance</option><option>Loan</option><option>Other</option>
        </Select>
      </FilterBar>

      <div className="mt-4">
        {error ? <ErrorState onRetry={load} /> : (
          <DataTable columns={columns} data={filtered} rowKey={(d) => d.id} loading={loading} pageSize={8} emptyTitle="No deductions found" />
        )}
      </div>
    </div>
  );
}
