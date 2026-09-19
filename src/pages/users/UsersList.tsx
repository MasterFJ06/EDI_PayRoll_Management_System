import { useEffect, useState } from "react";
import { UserPlus, Users as UsersIcon, Pencil, Trash2 } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { FilterBar } from "@/components/common/FilterBar";
import { SearchBar } from "@/components/common/SearchBar";
import { Select } from "@/components/ui/Select";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/common/StatusBadge";
import { EmployeeAvatar } from "@/components/common/EmployeeAvatar";
import { DataTable, type Column } from "@/components/tables/DataTable";
import { ErrorState } from "@/components/common/ErrorState";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { listUsers, deleteUser } from "@/services/userService";
import { ALL_ROLES } from "@/config/permissions";
import type { AppUser } from "@/types";
import { UserFormDialog } from "./UserFormDialog";

export default function UsersList() {
  const [users, setUsers] = useState<AppUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("all");
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<AppUser | null>(null);
  const [deleting, setDeleting] = useState<AppUser | null>(null);

  async function load() {
    setLoading(true);
    setError(false);
    try {
      const data = await listUsers();
      setUsers(data);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  const filtered = users.filter((u) => {
    const matchesSearch = `${u.firstName} ${u.lastName} ${u.username} ${u.email}`.toLowerCase().includes(search.toLowerCase());
    const matchesRole = roleFilter === "all" || u.role === roleFilter;
    return matchesSearch && matchesRole;
  });

  const columns: Column<AppUser>[] = [
    {
      key: "name", header: "User", sortValue: (u) => u.firstName,
      render: (u) => (
        <div className="flex items-center gap-2.5">
          <EmployeeAvatar firstName={u.firstName} lastName={u.lastName} size="sm" />
          <div>
            <p className="font-medium text-text">{u.firstName} {u.lastName}</p>
            <p className="text-xs text-text-muted">@{u.username}</p>
          </div>
        </div>
      ),
    },
    { key: "email", header: "Email", sortValue: (u) => u.email, render: (u) => <span className="text-text-muted">{u.email}</span> },
    { key: "role", header: "Role", sortValue: (u) => u.role, render: (u) => u.role },
    { key: "employeeId", header: "Employee ID", render: (u) => u.employeeId ?? "\u2014" },
    { key: "status", header: "Status", render: (u) => <StatusBadge status={u.status} /> },
    {
      key: "actions", header: "Actions", render: (u) => (
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" onClick={() => { setEditing(u); setFormOpen(true); }} aria-label="Edit user">
            <Pencil className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon" onClick={() => setDeleting(u)} aria-label="Delete user">
            <Trash2 className="h-4 w-4 text-danger" />
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="User Accounts"
        description="Manage application logins, roles and account status."
        icon={<UsersIcon className="h-5 w-5" />}
        actions={<Button onClick={() => { setEditing(null); setFormOpen(true); }}><UserPlus className="h-4 w-4" /> Add User</Button>}
      />

      <FilterBar>
        <SearchBar value={search} onChange={setSearch} placeholder="Search by name, username or email" className="w-full sm:w-72" />
        <Select value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)} className="w-full sm:w-48">
          <option value="all">All Roles</option>
          {ALL_ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
        </Select>
      </FilterBar>

      <div className="mt-4">
        {error ? (
          <ErrorState message="Unable to load users." onRetry={load} />
        ) : (
          <DataTable columns={columns} data={filtered} rowKey={(u) => u.id} loading={loading} emptyTitle="No users found" />
        )}
      </div>

      <UserFormDialog
        open={formOpen}
        onClose={() => setFormOpen(false)}
        user={editing}
        onSaved={() => { setFormOpen(false); load(); }}
      />

      <ConfirmDialog
        open={!!deleting}
        onClose={() => setDeleting(null)}
        title="Delete User"
        description={`Are you sure you want to delete ${deleting?.firstName} ${deleting?.lastName}? This action cannot be undone.`}
        confirmLabel="Delete"
        danger
        onConfirm={async () => { if (deleting) { await deleteUser(deleting.id); setDeleting(null); load(); } }}
      />
    </div>
  );
}
