import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { IdCard, UserPlus, Eye, Pencil, Power } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { FilterBar } from "@/components/common/FilterBar";
import { SearchBar } from "@/components/common/SearchBar";
import { Select } from "@/components/ui/Select";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/common/StatusBadge";
import { EmployeeAvatar } from "@/components/common/EmployeeAvatar";
import { DataTable, type Column } from "@/components/tables/DataTable";
import { ErrorState } from "@/components/common/ErrorState";
import { listEmployees, updateEmployee } from "@/services/employeeService";
import { departments, designations, departmentName, designationName } from "@/data/mockData";
import { formatDate } from "@/utils/format";
import { useAuth } from "@/context/AuthContext";
import type { Employee } from "@/types";
import { EmployeeFormDialog } from "./EmployeeFormDialog";

export default function EmployeeDirectory() {
  const { can } = useAuth();
  const navigate = useNavigate();
  const [items, setItems] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [search, setSearch] = useState("");
  const [deptFilter, setDeptFilter] = useState("all");
  const [desigFilter, setDesigFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Employee | null>(null);

  async function load() {
    setLoading(true); setError(false);
    try { setItems(await listEmployees()); } catch { setError(true); } finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []);

  const filtered = items.filter((e) => {
    const matchSearch = `${e.firstName} ${e.lastName} ${e.employeeCode} ${e.email}`.toLowerCase().includes(search.toLowerCase());
    const matchDept = deptFilter === "all" || e.departmentId === deptFilter;
    const matchDesig = desigFilter === "all" || e.designationId === desigFilter;
    const matchType = typeFilter === "all" || e.employmentType === typeFilter;
    const matchStatus = statusFilter === "all" || e.employmentStatus === statusFilter;
    return matchSearch && matchDept && matchDesig && matchType && matchStatus;
  });

  async function toggleStatus(e: Employee) {
    const next = e.employmentStatus === "Active" ? "Suspended" : "Active";
    await updateEmployee(e.id, { employmentStatus: next });
    load();
  }

  const columns: Column<Employee>[] = [
    { key: "name", header: "Employee", sortValue: (e) => e.firstName, render: (e) => (
      <div className="flex items-center gap-2.5">
        <EmployeeAvatar firstName={e.firstName} lastName={e.lastName} size="sm" />
        <div>
          <p className="font-medium text-text">{e.firstName} {e.lastName}</p>
          <p className="text-xs text-text-muted">{e.email}</p>
        </div>
      </div>
    ) },
    { key: "code", header: "Employee Code", sortValue: (e) => e.employeeCode, render: (e) => e.employeeCode },
    { key: "department", header: "Department", sortValue: (e) => departmentName(e.departmentId), render: (e) => departmentName(e.departmentId) },
    { key: "designation", header: "Designation", sortValue: (e) => designationName(e.designationId), render: (e) => designationName(e.designationId) },
    { key: "type", header: "Employment Type", render: (e) => e.employmentType },
    { key: "joining", header: "Joining Date", sortValue: (e) => e.joiningDate, render: (e) => formatDate(e.joiningDate) },
    { key: "status", header: "Status", render: (e) => <StatusBadge status={e.employmentStatus} /> },
    { key: "actions", header: "Actions", render: (e) => (
      <div className="flex items-center gap-1">
        <Button variant="ghost" size="icon" onClick={() => navigate(`/employees/${e.id}`)} aria-label="View"><Eye className="h-4 w-4" /></Button>
        {can("employee.update") && <Button variant="ghost" size="icon" onClick={() => { setEditing(e); setFormOpen(true); }} aria-label="Edit"><Pencil className="h-4 w-4" /></Button>}
        {can("employee.update") && <Button variant="ghost" size="icon" onClick={() => toggleStatus(e)} aria-label="Toggle status"><Power className="h-4 w-4 text-text-muted" /></Button>}
      </div>
    ) },
  ];

  return (
    <div>
      <PageHeader
        title="Employee Directory"
        description="Browse, search and manage employee records across the organization."
        icon={<IdCard className="h-5 w-5" />}
        actions={can("employee.create") ? <Button onClick={() => { setEditing(null); setFormOpen(true); }}><UserPlus className="h-4 w-4" /> Add Employee</Button> : undefined}
      />

      <FilterBar>
        <SearchBar value={search} onChange={setSearch} placeholder="Search by name, code or email" className="w-full sm:w-64" />
        <Select value={deptFilter} onChange={(e) => setDeptFilter(e.target.value)} className="w-full sm:w-44">
          <option value="all">All Departments</option>
          {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
        </Select>
        <Select value={desigFilter} onChange={(e) => setDesigFilter(e.target.value)} className="w-full sm:w-44">
          <option value="all">All Designations</option>
          {designations.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
        </Select>
        <Select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)} className="w-full sm:w-40">
          <option value="all">All Types</option>
          <option>Full-Time</option><option>Part-Time</option><option>Contract</option><option>Intern</option>
        </Select>
        <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="w-full sm:w-40">
          <option value="all">All Status</option>
          <option>Active</option><option>On Leave</option><option>Suspended</option><option>Terminated</option>
        </Select>
      </FilterBar>

      <div className="mt-4">
        {error ? <ErrorState onRetry={load} /> : (
          <DataTable columns={columns} data={filtered} rowKey={(e) => e.id} loading={loading} pageSize={7}
            emptyTitle="No employees found" emptyDescription="Try adjusting your search or filters." />
        )}
      </div>

      <EmployeeFormDialog open={formOpen} onClose={() => setFormOpen(false)} employee={editing} onSaved={() => { setFormOpen(false); load(); }} />
    </div>
  );
}
