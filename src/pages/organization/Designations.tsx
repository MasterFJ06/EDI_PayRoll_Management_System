import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Briefcase, Plus, Pencil, Trash2 } from "lucide-react";
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
import { listDesignations, createDesignation, updateDesignation, deleteDesignation } from "@/services/designationService";
import { departments, departmentName } from "@/data/mockData";
import type { Designation } from "@/types";

const schema = z.object({
  code: z.string().min(2, "Code is required"),
  name: z.string().min(2, "Designation name is required"),
  description: z.string().min(1, "Description is required"),
  hierarchyLevel: z.coerce.number().min(1).max(10),
  departmentId: z.string().min(1, "Department is required"),
  status: z.enum(["Active", "Inactive"]),
});
type FormValues = z.infer<typeof schema>;

export default function Designations() {
  const [items, setItems] = useState<Designation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [search, setSearch] = useState("");
  const [deptFilter, setDeptFilter] = useState("all");
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Designation | null>(null);
  const [deleting, setDeleting] = useState<Designation | null>(null);

  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { status: "Active", hierarchyLevel: 3 },
  });

  async function load() {
    setLoading(true); setError(false);
    try { setItems(await listDesignations()); } catch { setError(true); } finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []);

  function openCreate() {
    setEditing(null);
    reset({ code: "", name: "", description: "", hierarchyLevel: 3, departmentId: departments[0].id, status: "Active" });
    setFormOpen(true);
  }
  function openEdit(d: Designation) {
    setEditing(d);
    reset({ code: d.code, name: d.name, description: d.description, hierarchyLevel: d.hierarchyLevel, departmentId: d.departmentId, status: d.status });
    setFormOpen(true);
  }

  async function onSubmit(values: FormValues) {
    if (editing) {
      await updateDesignation(editing.id, { ...values, updatedDate: new Date().toISOString().slice(0, 10) });
    } else {
      await createDesignation({
        id: `DS${Date.now()}`, ...values,
        createdDate: new Date().toISOString().slice(0, 10), updatedDate: new Date().toISOString().slice(0, 10),
      });
    }
    setFormOpen(false);
    load();
  }

  const filtered = items.filter((d) => {
    const matchSearch = `${d.name} ${d.code}`.toLowerCase().includes(search.toLowerCase());
    const matchDept = deptFilter === "all" || d.departmentId === deptFilter;
    return matchSearch && matchDept;
  });

  const columns: Column<Designation>[] = [
    { key: "name", header: "Designation", sortValue: (d) => d.name, render: (d) => (
      <div><p className="font-medium text-text">{d.name}</p><p className="text-xs text-text-muted">{d.code}</p></div>
    ) },
    { key: "department", header: "Department", sortValue: (d) => departmentName(d.departmentId), render: (d) => departmentName(d.departmentId) },
    { key: "level", header: "Hierarchy Level", sortValue: (d) => d.hierarchyLevel, render: (d) => <span className="text-text-muted">L{d.hierarchyLevel}</span> },
    { key: "description", header: "Description", render: (d) => <span className="text-text-muted line-clamp-1 max-w-xs block">{d.description}</span> },
    { key: "status", header: "Status", render: (d) => <StatusBadge status={d.status} /> },
    { key: "actions", header: "Actions", render: (d) => (
      <div className="flex items-center gap-1">
        <Button variant="ghost" size="icon" onClick={() => openEdit(d)} aria-label="Edit"><Pencil className="h-4 w-4" /></Button>
        <Button variant="ghost" size="icon" onClick={() => setDeleting(d)} aria-label="Delete"><Trash2 className="h-4 w-4 text-danger" /></Button>
      </div>
    ) },
  ];

  return (
    <div>
      <PageHeader
        title="Designation Management"
        description="Define job titles, hierarchy levels and their parent departments."
        icon={<Briefcase className="h-5 w-5" />}
        actions={<Button onClick={openCreate}><Plus className="h-4 w-4" /> Add Designation</Button>}
      />

      <FilterBar>
        <SearchBar value={search} onChange={setSearch} placeholder="Search designations" className="w-full sm:w-72" />
        <Select value={deptFilter} onChange={(e) => setDeptFilter(e.target.value)} className="w-full sm:w-52">
          <option value="all">All Departments</option>
          {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
        </Select>
      </FilterBar>

      <div className="mt-4">
        {error ? <ErrorState onRetry={load} /> : (
          <DataTable columns={columns} data={filtered} rowKey={(d) => d.id} loading={loading} emptyTitle="No designations found" />
        )}
      </div>

      <Dialog
        open={formOpen} onClose={() => setFormOpen(false)}
        title={editing ? "Edit Designation" : "Add Designation"} size="md"
        footer={<>
          <Button variant="outline" onClick={() => setFormOpen(false)}>Cancel</Button>
          <Button onClick={handleSubmit(onSubmit)} loading={isSubmitting}>{editing ? "Save Changes" : "Create Designation"}</Button>
        </>}
      >
        <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label required>Designation Code</Label>
              <Input {...register("code")} error={!!errors.code} placeholder="e.g. SE" />
              {errors.code && <p className="mt-1 text-xs text-danger">{errors.code.message}</p>}
            </div>
            <div>
              <Label required>Hierarchy Level</Label>
              <Input type="number" min={1} max={10} {...register("hierarchyLevel")} />
            </div>
          </div>
          <div>
            <Label required>Designation Name</Label>
            <Input {...register("name")} error={!!errors.name} />
            {errors.name && <p className="mt-1 text-xs text-danger">{errors.name.message}</p>}
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label required>Department</Label>
              <Select {...register("departmentId")}>
                {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
              </Select>
            </div>
            <div>
              <Label required>Status</Label>
              <Select {...register("status")}><option value="Active">Active</option><option value="Inactive">Inactive</option></Select>
            </div>
          </div>
          <div>
            <Label required>Description</Label>
            <Textarea rows={3} {...register("description")} />
            {errors.description && <p className="mt-1 text-xs text-danger">{errors.description.message}</p>}
          </div>
        </form>
      </Dialog>

      <ConfirmDialog
        open={!!deleting} onClose={() => setDeleting(null)}
        title="Delete Designation" danger confirmLabel="Delete"
        description={`Delete "${deleting?.name}"? This cannot be undone.`}
        onConfirm={async () => { if (deleting) { await deleteDesignation(deleting.id); setDeleting(null); load(); } }}
      />
    </div>
  );
}
