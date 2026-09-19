import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { DownloadCloud, Plus, Download } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import { Label } from "@/components/ui/Label";
import { Dialog } from "@/components/ui/Dialog";
import { StatusBadge } from "@/components/common/StatusBadge";
import { DataTable, type Column } from "@/components/tables/DataTable";
import { ErrorState } from "@/components/common/ErrorState";
import { listExports, requestExport } from "@/services/reportService";
import { formatDateTime } from "@/utils/format";
import { useAuth } from "@/context/AuthContext";
import type { ReportExport } from "@/types";

const schema = z.object({
  reportType: z.enum(["Salary Report", "Attendance Summary", "Leave Report", "Payroll Summary"]),
  format: z.enum(["PDF", "Excel", "CSV"]),
});
type FormValues = z.infer<typeof schema>;

export default function Exports() {
  const { user } = useAuth();
  const [items, setItems] = useState<ReportExport[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [formOpen, setFormOpen] = useState(false);

  const { register, handleSubmit, formState: { isSubmitting } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { reportType: "Salary Report", format: "PDF" },
  });

  async function load() {
    setLoading(true); setError(false);
    try { setItems(await listExports()); } catch { setError(true); } finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []);

  async function onSubmit(values: FormValues) {
    const ext = values.format === "PDF" ? "pdf" : values.format === "Excel" ? "xlsx" : "csv";
    await requestExport({
      id: `EXP${Date.now()}`, reportId: `RPT-${Date.now()}`, reportType: values.reportType, format: values.format,
      requestedBy: `${user?.firstName} ${user?.lastName}`, fileName: `${values.reportType.toLowerCase().replace(/\s/g, "-")}.${ext}`,
      timestamp: new Date().toISOString(), status: "Completed", downloadLocation: `/exports/report.${ext}`, fileSize: "215 KB",
    });
    setFormOpen(false);
    load();
  }

  const columns: Column<ReportExport>[] = [
    { key: "type", header: "Report Type", sortValue: (e) => e.reportType, render: (e) => <span className="font-medium text-text">{e.reportType}</span> },
    { key: "format", header: "Format", render: (e) => e.format },
    { key: "requestedBy", header: "Requested By", render: (e) => e.requestedBy },
    { key: "fileName", header: "File", render: (e) => <span className="font-mono text-xs text-text-muted">{e.fileName}</span> },
    { key: "timestamp", header: "Timestamp", sortValue: (e) => e.timestamp, render: (e) => formatDateTime(e.timestamp) },
    { key: "size", header: "Size", render: (e) => e.fileSize },
    { key: "status", header: "Status", render: (e) => <StatusBadge status={e.status} /> },
    { key: "actions", header: "Actions", render: (e) => (
      e.status === "Completed" ? <Button variant="outline" size="sm"><Download className="h-3.5 w-3.5" /> Download</Button> : <span className="text-xs text-text-muted">Processing\u2026</span>
    ) },
  ];

  return (
    <div>
      <PageHeader
        title="Export Reports"
        description="Request and download report exports in PDF, Excel or CSV format."
        icon={<DownloadCloud className="h-5 w-5" />}
        actions={<Button onClick={() => setFormOpen(true)}><Plus className="h-4 w-4" /> Request Export</Button>}
      />

      {error ? <ErrorState onRetry={load} /> : (
        <DataTable columns={columns} data={items} rowKey={(e) => e.id} loading={loading} pageSize={8} emptyTitle="No exports requested yet" />
      )}

      <Dialog
        open={formOpen} onClose={() => setFormOpen(false)} title="Request Report Export" size="sm"
        footer={<>
          <Button variant="outline" onClick={() => setFormOpen(false)}>Cancel</Button>
          <Button onClick={handleSubmit(onSubmit)} loading={isSubmitting}>Generate</Button>
        </>}
      >
        <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
          <div>
            <Label required>Report Type</Label>
            <Select {...register("reportType")}>
              <option>Salary Report</option><option>Attendance Summary</option><option>Leave Report</option><option>Payroll Summary</option>
            </Select>
          </div>
          <div>
            <Label required>Export Format</Label>
            <Select {...register("format")}><option value="PDF">PDF</option><option value="Excel">Excel</option><option value="CSV">CSV</option></Select>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
