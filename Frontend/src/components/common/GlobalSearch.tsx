import { useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search } from "lucide-react";
import { useClickOutside } from "@/hooks/useClickOutside";
import { employees, departments, payrollRecords, payslips } from "@/data/mockData";
import { monthLabel } from "@/utils/format";

interface ResultGroup {
  label: string;
  items: { key: string; title: string; subtitle: string; path: string }[];
}

export function GlobalSearch() {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  useClickOutside(ref, () => setOpen(false), open);

  const groups: ResultGroup[] = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (q.length < 2) return [];

    const empMatches = employees
      .filter((e) => `${e.firstName} ${e.lastName} ${e.employeeCode}`.toLowerCase().includes(q))
      .slice(0, 4)
      .map((e) => ({ key: e.id, title: `${e.employeeCode} \u2014 ${e.firstName} ${e.lastName}`, subtitle: "Employee", path: "/employees" }));

    const deptMatches = departments
      .filter((d) => d.name.toLowerCase().includes(q) || d.code.toLowerCase().includes(q))
      .slice(0, 3)
      .map((d) => ({ key: d.id, title: d.name, subtitle: "Department", path: "/organization/departments" }));

    const payrollMatches = payrollRecords
      .filter((p) => monthLabel(p.payrollMonth).toLowerCase().includes(q) || p.employeeId.toLowerCase().includes(q))
      .slice(0, 3)
      .map((p) => ({ key: p.id, title: `${monthLabel(p.payrollMonth)} \u2014 ${p.employeeId}`, subtitle: "Payroll", path: "/payroll/processing" }));

    const payslipMatches = payslips
      .filter((p) => p.id.toLowerCase().includes(q) || p.employeeId.toLowerCase().includes(q))
      .slice(0, 3)
      .map((p) => ({ key: p.id, title: `${p.id} \u2014 ${monthLabel(p.payrollMonth)}`, subtitle: "Payslip", path: "/payroll/payslips" }));

    const groupsList: ResultGroup[] = [];
    if (empMatches.length) groupsList.push({ label: "Employees", items: empMatches });
    if (deptMatches.length) groupsList.push({ label: "Departments", items: deptMatches });
    if (payrollMatches.length) groupsList.push({ label: "Payroll", items: payrollMatches });
    if (payslipMatches.length) groupsList.push({ label: "Payslips", items: payslipMatches });
    return groupsList;
  }, [query]);

  return (
    <div className="relative hidden w-full max-w-sm md:block" ref={ref}>
      <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
      <input
        value={query}
        onChange={(e) => { setQuery(e.target.value); setOpen(true); }}
        onFocus={() => setOpen(true)}
        placeholder="Search employees, departments, payroll..."
        className="h-9 w-full rounded-lg border border-border bg-slate-50 pl-9 pr-3 text-sm text-text placeholder:text-text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary focus-visible:bg-white"
      />
      {open && query.trim().length >= 2 && (
        <div className="absolute left-0 right-0 z-30 mt-2 max-h-96 overflow-y-auto rounded-xl border border-border bg-white shadow-xl scrollbar-thin">
          {groups.length === 0 && (
            <p className="px-4 py-6 text-center text-sm text-text-muted">No results for "{query}"</p>
          )}
          {groups.map((group) => (
            <div key={group.label} className="border-b border-border py-2 last:border-0">
              <p className="px-4 pb-1 text-[10px] font-semibold uppercase tracking-wide text-text-muted">{group.label}</p>
              {group.items.map((item) => (
                <button
                  key={item.key}
                  onClick={() => { navigate(item.path); setOpen(false); setQuery(""); }}
                  className="flex w-full flex-col px-4 py-1.5 text-left hover:bg-slate-50"
                >
                  <span className="text-sm text-text">{item.title}</span>
                  <span className="text-[11px] text-text-muted">{item.subtitle}</span>
                </button>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
