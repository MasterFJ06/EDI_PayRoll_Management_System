import { useEffect, useState } from "react";
import { DatabaseBackup, Plus, RotateCcw } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import { Label } from "@/components/ui/Label";
import { Dialog } from "@/components/ui/Dialog";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { StatusBadge } from "@/components/common/StatusBadge";
import { DataTable, type Column } from "@/components/tables/DataTable";
import { ErrorState } from "@/components/common/ErrorState";
import { listBackups, createBackup, restoreBackup } from "@/services/backupService";
import { formatDateTime } from "@/utils/format";
import { useAuth } from "@/context/AuthContext";
import type { Backup } from "@/types";

export default function BackupRestore() {
  const { user } = useAuth();
  const [items, setItems] = useState<Backup[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [backupType, setBackupType] = useState<Backup["type"]>("Full");
  const [restoring, setRestoring] = useState<Backup | null>(null);
  const [creating, setCreating] = useState(false);
  const [restoringLoading, setRestoringLoading] = useState(false);

  async function load() {
    setLoading(true); setError(false);
    try { setItems(await listBackups()); } catch { setError(true); } finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []);

  async function handleCreate() {
    setCreating(true);
    await createBackup(backupType, `${user?.firstName} ${user?.lastName}`);
    setCreating(false);
    setCreateOpen(false);
    load();
  }

  async function handleRestore() {
    if (!restoring) return;
    setRestoringLoading(true);
    await restoreBackup(restoring.id);
    setRestoringLoading(false);
    setRestoring(null);
    load();
  }

  const columns: Column<Backup>[] = [
    { key: "id", header: "Backup ID", render: (b) => <span className="font-mono text-xs text-text-muted">{b.id}</span> },
    { key: "type", header: "Type", render: (b) => b.type },
    { key: "timestamp", header: "Timestamp", sortValue: (b) => b.timestamp, render: (b) => formatDateTime(b.timestamp) },
    { key: "size", header: "Size", render: (b) => b.size },
    { key: "createdBy", header: "Created By", render: (b) => b.createdBy },
    { key: "status", header: "Backup Status", render: (b) => <StatusBadge status={b.status} /> },
    { key: "restoreStatus", header: "Restore Status", render: (b) => <StatusBadge status={b.restoreStatus} /> },
    { key: "actions", header: "Actions", render: (b) => (
      b.status === "Completed" ? <Button variant="outline" size="sm" onClick={() => setRestoring(b)}><RotateCcw className="h-3.5 w-3.5" /> Restore</Button> : null
    ) },
  ];

  return (
    <div>
      <PageHeader
        title="Backup & Restore"
        description="System-level backups of the payroll database. Restoring always requires confirmation."
        icon={<DatabaseBackup className="h-5 w-5" />}
        actions={<Button onClick={() => setCreateOpen(true)}><Plus className="h-4 w-4" /> Create Backup</Button>}
      />

      {error ? <ErrorState onRetry={load} /> : (
        <DataTable columns={columns} data={items} rowKey={(b) => b.id} loading={loading} pageSize={8} emptyTitle="No backups found" />
      )}

      <Dialog
        open={createOpen} onClose={() => setCreateOpen(false)} title="Create Backup" size="sm"
        footer={<>
          <Button variant="outline" onClick={() => setCreateOpen(false)}>Cancel</Button>
          <Button onClick={handleCreate} loading={creating}>Create Backup</Button>
        </>}
      >
        <Label required>Backup Type</Label>
        <Select value={backupType} onChange={(e) => setBackupType(e.target.value as Backup["type"])}>
          <option value="Full">Full</option>
          <option value="Incremental">Incremental</option>
          <option value="Differential">Differential</option>
        </Select>
      </Dialog>

      <ConfirmDialog
        open={!!restoring} onClose={() => setRestoring(null)} onConfirm={handleRestore} loading={restoringLoading}
        title="Restore Backup" danger confirmLabel="Restore"
        description={`This will restore the system to the state captured in backup ${restoring?.id}. Any data created after this backup will be lost. This action cannot be undone.`}
      />
    </div>
  );
}
