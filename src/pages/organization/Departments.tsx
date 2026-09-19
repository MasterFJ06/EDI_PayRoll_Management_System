import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Building2, Plus, Pencil, Trash2, Users } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { FilterBar } from "@/components/common/FilterBar";
import { SearchBar } from "@/components/common/SearchBar";
import { Select } from "@/components/ui/Select";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Textarea } from "@/components/ui/Textarea";
import { Dialog } from "@/components/ui/Dialog";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { StatusBadge } from "@/components/common/StatusBadge";
import { DataTable, type Column } from "@/components/tables/DataTable";
import { ErrorState } from "@/components/common/ErrorState";
import { listDepartments, createDepartment, updateDepartment, deleteDepartment } from "@/services/departmentService";
import { formatDate } from "@/utils/format";
import type { Department } from "@/types";

const schema = z.object({
  code: z.string().min(2, "Code is required"),
  name: z.string().min(2, "Department name is required"),
  description: z.string().min(1, "Description is required"),
  headName: z.string().optional(),
  status: z.enum(["Active", "Inactive"]),
});
type FormValues = z.infer<typeof schema>;

export default function Departments() {
  const [items, setItems] = useState<Department[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Department | null>(null);
  const [deleting, setDeleting] = useState<Department | null>(null);

  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { status: "Active" },
  });

  async function load() {
    setLoading(true); setError(false);
    try { setItems(await listDepartments()); } catch { setError(true); } finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []);

  function openCreate() {
    setEditing(null);
    reset({ code: "", name: "", description: "", headName: "", status: "Active" });
    setFormOpen(true);
  }
  function openEdit(d: Department) {
    setEditing(d);
    reset({ code: d.code, name: d.name, description: d.description, headName: d.headName ?? "", status: d.status });
    setFormOpen(true);
  }

  async function onSubmit(values: FormValues) {
    if (editing) {
      await updateDepartment(editing.id, { ...values, headName: values.headName || null, updatedDate: new Date().toISOString().slice(0, 10) });
    } else {
      await createDepartment({
        id: `D${Date.now()}`, ...values, headEmployeeId: null, headName: values.headName || null,
        employeeCount: 0, createdDate: new Date().toISOString().slice(0, 10), updatedDate: new Date().toISOString().slice(0, 10),
      });
    }
    setFormOpen(false);
    load();
  }

  const filtered = items.filter((d) => {
    const matchSearch = `${d.name} ${d.code}`.toLowerCase().includes(search.toLowerCase());
    const matchStatus = statusFilter === "all" || d.status === statusFilter;
    return matchSearch && matchStatus;
  });

  const columns: Column<Department>[] = [
    {
      key: "name", header: "Department", sortValue: (d) => d.name,
      render: (d) => (
        <div>
          <p className="font-medium text-text">{d.name}</p>
          <p className="text-xs text-text-muted">{d.code}</p>
        </div>
      ),
    },
    { key: "description", header: "Description", render: (d) => <span className="text-text-muted line-clamp-1 max-w-xs block">{d.description}</span> },
    { key: "head", header: "Department Head", render: (d) => d.headName ?? "\u2014" },
    { key: "count", header: "Employees", sortValue: (d) => d.employeeCount, render: (d) => <span className="inline-flex items-center gap-1"><Users className="h-3.5 w-3.5 text-text-muted" />{d.employeeCount}</span> },
    { key: "status", header: "Status", render: (d) => <StatusBadge status={d.status} /> },
    { key: "updated", header: "Updated", sortValue: (d) => d.updatedDate, render: (d) => formatDate(d.updatedDate) },
    {
      key: "actions", header: "Actions", render: (d) => (
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" onClick={() => openEdit(d)} aria-label="Edit"><Pencil className="h-4 w-4" /></Button>
          <Button variant="ghost" size="icon" onClick={() => setDeleting(d)} aria-label="Delete"><Trash2 className="h-4 w-4 text-danger" /></Button>
        </div>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Department Management"
        description="Organize your company into departments and assign department heads."
        icon={<Building2 className="h-5 w-5" />}
        actions={<Button onClick={openCreate}><Plus className="h-4 w-4" /> Add Department</Button>}
      />

      <FilterBar>
        <SearchBar value={search} onChange={setSearch} placeholder="Search departments" className="w-full sm:w-72" />
        <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="w-full sm:w-40">
          <option value="all">All Status</option>
          <option value="Active">Active</option>
          <option value="Inactive">Inactive</option>
        </Select>
      </FilterBar>

      <div className="mt-4">
        {error ? <ErrorState onRetry={load} /> : (
          <DataTable columns={columns} data={filtered} rowKey={(d) => d.id} loading={loading} emptyTitle="No departments found" />
        )}
      </div>

      <Dialog
        open={formOpen} onClose={() => setFormOpen(false)}
        title={editing ? "Edit Department" : "Add Department"} size="md"
        footer={<>
          <Button variant="outline" onClick={() => setFormOpen(false)}>Cancel</Button>
          <Button onClick={handleSubmit(onSubmit)} loading={isSubmitting}>{editing ? "Save Changes" : "Create Department"}</Button>
        </>}
      >
        <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label required>Department Code</Label>
              <Input {...register("code")} error={!!errors.code} placeholder="e.g. IT" />
              {errors.code && <p className="mt-1 text-xs text-danger">{errors.code.message}</p>}
            </div>
            <div>
              <Label required>Status</Label>
              <Select {...register("status")}><option value="Active">Active</option><option value="Inactive">Inactive</option></Select>
            </div>
          </div>
          <div>
            <Label required>Department Name</Label>
            <Input {...register("name")} error={!!errors.name} />
            {errors.name && <p className="mt-1 text-xs text-danger">{errors.name.message}</p>}
          </div>
          <div>
            <Label required>Description</Label>
            <Textarea rows={3} {...register("description")} />
            {errors.description && <p className="mt-1 text-xs text-danger">{errors.description.message}</p>}
          </div>
          <div>
            <Label>Department Head</Label>
            <Input {...register("headName")} placeholder="e.g. Amit Kulkarni (optional)" />
          </div>
        </form>
      </Dialog>

      <ConfirmDialog
        open={!!deleting} onClose={() => setDeleting(null)}
        title="Delete Department" danger confirmLabel="Delete"
        description={`Delete "${deleting?.name}"? Employees in this department will need to be reassigned.`}
        onConfirm={async () => { if (deleting) { await deleteDepartment(deleting.id); setDeleting(null); load(); } }}
      />
    </div>
  );
}
