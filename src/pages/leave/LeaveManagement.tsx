import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { CalendarClock, Plus, Check, X, Ban } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { FilterBar } from "@/components/common/FilterBar";
import { SearchBar } from "@/components/common/SearchBar";
import { Select } from "@/components/ui/Select";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Textarea } from "@/components/ui/Textarea";
import { Dialog } from "@/components/ui/Dialog";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Card, CardContent } from "@/components/ui/Card";
import { DataTable, type Column } from "@/components/tables/DataTable";
import { ErrorState } from "@/components/common/ErrorState";
import { listLeaves, createLeave, approveLeave, rejectLeave, cancelLeave } from "@/services/leaveService";
import { employees, employeeName, leaveBalances } from "@/data/mockData";
import { formatDate } from "@/utils/format";
import { useAuth } from "@/context/AuthContext";
import type { LeaveRequest, LeaveType } from "@/types";

const schema = z.object({
  employeeId: z.string().min(1, "Employee is required"),
  leaveType: z.enum(["Casual", "Sick", "Earned", "Maternity", "Paternity", "Unpaid"]),
  startDate: z.string().min(1, "Start date is required"),
  endDate: z.string().min(1, "End date is required"),
  reason: z.string().min(3, "Please provide a reason"),
}).refine((d) => d.endDate >= d.startDate, { message: "End date cannot be before start date", path: ["endDate"] });
type FormValues = z.infer<typeof schema>;

function daysBetween(start: string, end: string) {
  const s = new Date(start), e = new Date(end);
  return Math.round((e.getTime() - s.getTime()) / 86400000) + 1;
}

export default function LeaveManagement() {
  const { user, can } = useAuth();
  const [items, setItems] = useState<LeaveRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");
  const [formOpen, setFormOpen] = useState(false);

  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { leaveType: "Casual" },
  });

  useEffect(() => {
    if (formOpen) {
      reset({ leaveType: "Casual", employeeId: can("leave.view.all") ? "" : (user?.employeeId ?? ""), startDate: "", endDate: "", reason: "" });
    }
  }, [formOpen]); // eslint-disable-line react-hooks/exhaustive-deps

  async function load() {
    setLoading(true); setError(false);
    try { setItems(await listLeaves()); } catch { setError(true); } finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []);

  const scopedItems = can("leave.view.all") ? items : items.filter((l) => l.employeeId === user?.employeeId);

  const filtered = scopedItems.filter((l) => {
    const matchSearch = employeeName(l.employeeId).toLowerCase().includes(search.toLowerCase());
    const matchStatus = statusFilter === "all" || l.status === statusFilter;
    const matchType = typeFilter === "all" || l.leaveType === typeFilter;
    return matchSearch && matchStatus && matchType;
  });

  const myBalances = leaveBalances.filter((b) => b.employeeId === user?.employeeId);

  async function onSubmit(values: FormValues) {
    await createLeave({
      id: `LV${Date.now()}`, ...values, totalDays: daysBetween(values.startDate, values.endDate),
      status: "Pending", approverId: null, appliedDate: new Date().toISOString().slice(0, 10), approvalDate: null,
    });
    setFormOpen(false);
    reset();
    load();
  }

  async function handleApprove(l: LeaveRequest) { await approveLeave(l.id, user?.id ?? ""); load(); }
  async function handleReject(l: LeaveRequest) { await rejectLeave(l.id, user?.id ?? ""); load(); }
  async function handleCancel(l: LeaveRequest) { await cancelLeave(l.id); load(); }

  const columns: Column<LeaveRequest>[] = [
    { key: "employee", header: "Employee", sortValue: (l) => employeeName(l.employeeId), render: (l) => <span className="font-medium text-text">{employeeName(l.employeeId)}</span> },
    { key: "type", header: "Leave Type", render: (l) => l.leaveType },
    { key: "dates", header: "Dates", sortValue: (l) => l.startDate, render: (l) => `${formatDate(l.startDate)} \u2013 ${formatDate(l.endDate)}` },
    { key: "days", header: "Days", sortValue: (l) => l.totalDays, render: (l) => l.totalDays },
    { key: "reason", header: "Reason", render: (l) => <span className="text-text-muted line-clamp-1 max-w-[180px] block">{l.reason}</span> },
    { key: "applied", header: "Applied", sortValue: (l) => l.appliedDate, render: (l) => formatDate(l.appliedDate) },
    { key: "status", header: "Status", render: (l) => <StatusBadge status={l.status} /> },
    { key: "actions", header: "Actions", render: (l) => (
      <div className="flex items-center gap-1">
        {l.status === "Pending" && can("leave.approve") && (
          <Button variant="ghost" size="icon" onClick={() => handleApprove(l)} aria-label="Approve"><Check className="h-4 w-4 text-success" /></Button>
        )}
        {l.status === "Pending" && can("leave.reject") && (
          <Button variant="ghost" size="icon" onClick={() => handleReject(l)} aria-label="Reject"><X className="h-4 w-4 text-danger" /></Button>
        )}
        {l.status === "Pending" && l.employeeId === user?.employeeId && (
          <Button variant="ghost" size="icon" onClick={() => handleCancel(l)} aria-label="Cancel"><Ban className="h-4 w-4 text-text-muted" /></Button>
        )}
      </div>
    ) },
  ];

  return (
    <div>
      <PageHeader
        title="Leave Management"
        description={can("leave.view.all") ? "Review, approve and track leave requests across the organization." : "Apply for leave and track your requests and balances."}
        icon={<CalendarClock className="h-5 w-5" />}
        actions={can("leave.apply") ? <Button onClick={() => setFormOpen(true)}><Plus className="h-4 w-4" /> Apply Leave</Button> : undefined}
      />

      {myBalances.length > 0 && (
        <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-3">
          {myBalances.map((b) => (
            <Card key={b.leaveType}><CardContent className="py-4 text-center">
              <p className="text-2xl font-semibold text-text">{b.balance}</p>
              <p className="text-xs text-text-muted">{b.leaveType} days remaining</p>
            </CardContent></Card>
          ))}
        </div>
      )}

      <FilterBar>
        <SearchBar value={search} onChange={setSearch} placeholder="Search by employee" className="w-full sm:w-64" />
        <Select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)} className="w-full sm:w-40">
          <option value="all">All Types</option>
          <option>Casual</option><option>Sick</option><option>Earned</option><option>Maternity</option><option>Paternity</option><option>Unpaid</option>
        </Select>
        <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="w-full sm:w-40">
          <option value="all">All Status</option>
          <option>Pending</option><option>Approved</option><option>Rejected</option><option>Cancelled</option>
        </Select>
      </FilterBar>

      <div className="mt-4">
        {error ? <ErrorState onRetry={load} /> : (
          <DataTable columns={columns} data={filtered} rowKey={(l) => l.id} loading={loading} pageSize={8} emptyTitle="No leave requests found" />
        )}
      </div>

      <Dialog
        open={formOpen} onClose={() => setFormOpen(false)} title="Apply for Leave" size="md"
        footer={<>
          <Button variant="outline" onClick={() => setFormOpen(false)}>Cancel</Button>
          <Button onClick={handleSubmit(onSubmit)} loading={isSubmitting}>Submit Request</Button>
        </>}
      >
        <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
          {can("leave.view.all") && (
            <div>
              <Label required>Employee</Label>
              <Select {...register("employeeId")} error={!!errors.employeeId}>
                <option value="">Select employee</option>
                {employees.map((e) => <option key={e.id} value={e.id}>{e.firstName} {e.lastName}</option>)}
              </Select>
            </div>
          )}
          {!can("leave.view.all") && <input type="hidden" {...register("employeeId")} />}
          <div>
            <Label required>Leave Type</Label>
            <Select {...register("leaveType")}>
              <option value="Casual">Casual</option><option value="Sick">Sick</option><option value="Earned">Earned</option>
              <option value="Maternity">Maternity</option><option value="Paternity">Paternity</option><option value="Unpaid">Unpaid</option>
            </Select>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div><Label required>Start Date</Label><Input type="date" {...register("startDate")} error={!!errors.startDate} /></div>
            <div><Label required>End Date</Label><Input type="date" {...register("endDate")} error={!!errors.endDate} />{errors.endDate && <p className="mt-1 text-xs text-danger">{errors.endDate.message}</p>}</div>
          </div>
          <div>
            <Label required>Reason</Label>
            <Textarea rows={3} {...register("reason")} placeholder="Briefly describe the reason for leave" />
            {errors.reason && <p className="mt-1 text-xs text-danger">{errors.reason.message}</p>}
          </div>
        </form>
      </Dialog>
    </div>
  );
}
