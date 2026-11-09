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
import { listLeaves, createLeave, approveLeave, rejectLeave, cancelLeave, listLeaveBalances } from "@/services/leaveService";
import { listEmployees } from "@/services/employeeService";
import { formatDate } from "@/utils/format";
import { useAuth } from "@/context/AuthContext";
import type { LeaveRequest, LeaveBalance, Employee } from "@/types";

const schema = z
  .object({
    employeeId: z.string().optional(),
    leaveType: z.enum(["Casual", "Sick", "Earned", "Maternity", "Paternity", "Unpaid"]),
    startDate: z.string().min(1, "Start date is required"),
    endDate: z.string().min(1, "End date is required"),
    reason: z.string().min(3, "Please provide a reason (minimum 3 characters)"),
  })
  .refine((d) => !d.startDate || !d.endDate || d.endDate >= d.startDate, {
    message: "End date cannot be before start date",
    path: ["endDate"],
  });
type FormValues = z.infer<typeof schema>;

function daysBetween(start: string, end: string) {
  const s = new Date(start), e = new Date(end);
  return Math.round((e.getTime() - s.getTime()) / 86400000) + 1;
}

export default function LeaveManagement() {
  const { user, can } = useAuth();
  const [items, setItems] = useState<LeaveRequest[]>([]);
  const [employeesList, setEmployeesList] = useState<Employee[]>([]);
  const [balances, setBalances] = useState<LeaveBalance[]>([]);
  const [, setBalancesLoading] = useState(true);
  const [balancesError, setBalancesError] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [search, setSearch] = useState("");
  const [employeeFilter, setEmployeeFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");
  const [formOpen, setFormOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { leaveType: "Casual" },
  });

  useEffect(() => {
    if (formOpen) {
      setSubmitError(null);
      const defaultEmpId = can("leave.view.all")
        ? (employeesList[0]?.id || employeesList[0]?.employeeCode || "")
        : (user?.employeeId || employeesList[0]?.id || employeesList[0]?.employeeCode || "EMP001");
      reset({
        leaveType: "Casual",
        employeeId: defaultEmpId,
        startDate: "",
        endDate: "",
        reason: "",
      });
    }
  }, [formOpen, employeesList, can, user?.employeeId, reset]);

  async function load() {
    setLoading(true);
    setError(false);
    try {
      const [leavesData, empData] = await Promise.all([
        listLeaves(),
        listEmployees().catch(() => [] as Employee[]),
      ]);
      setItems(leavesData);
      setEmployeesList(empData);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }

    try {
      setBalancesLoading(true);
      setBalancesError(false);
      const balancesData = await listLeaveBalances(user?.employeeId || undefined);
      const userBalances = user?.employeeId
        ? balancesData.filter((b) => b.employeeId === user.employeeId || (b as any).employee_id === user.employeeId)
        : balancesData;
      setBalances(userBalances);
    } catch {
      setBalancesError(true);
      setBalances([]);
    } finally {
      setBalancesLoading(false);
    }
  }
  useEffect(() => { load(); }, [user?.employeeId]);

  function getEmployeeName(id: string): string {
    const emp = employeesList.find((e) => e.id === id || e.employeeCode === id);
    if (emp) return `${emp.firstName} ${emp.lastName}`;
    return id || "Unknown";
  }

  const userEmpId = user?.employeeId;
  const scopedItems = can("leave.view.all")
    ? items
    : items.filter((l) => {
        const itemEmpId = l.employeeId || (l as any).employee_id;
        return !userEmpId || itemEmpId === userEmpId || itemEmpId === "EMP001";
      });

  const filtered = scopedItems.filter((l) => {
    const empId = l.employeeId || (l as any).employee_id || "";
    const empName = getEmployeeName(empId);
    const lType = l.leaveType || (l as any).leave_type || "";
    const lStatus = l.status || "Pending";

    const matchSearch =
      empName.toLowerCase().includes(search.toLowerCase()) ||
      empId.toLowerCase().includes(search.toLowerCase());
    const matchEmployee = employeeFilter === "all" || empId === employeeFilter;
    const matchStatus = statusFilter === "all" || lStatus === statusFilter;
    const matchType = typeFilter === "all" || lType === typeFilter;
    return matchSearch && matchEmployee && matchStatus && matchType;
  });

  async function onSubmit(values: FormValues) {
    setSubmitting(true);
    setSubmitError(null);
    try {
      const resolvedEmpId =
        values.employeeId ||
        user?.employeeId ||
        employeesList[0]?.id ||
        employeesList[0]?.employeeCode ||
        "EMP001";

      if (can("leave.view.all") && !resolvedEmpId) {
        setSubmitError("Please select an employee.");
        setSubmitting(false);
        return;
      }

      await createLeave({
        id: `LV${Date.now()}`,
        employeeId: resolvedEmpId,
        leaveType: values.leaveType,
        startDate: values.startDate,
        endDate: values.endDate,
        totalDays: daysBetween(values.startDate, values.endDate),
        reason: values.reason,
        status: "Pending",
        approverId: null,
        appliedDate: new Date().toISOString().slice(0, 10),
        approvalDate: null,
      });

      setFormOpen(false);
      reset();
      await load();
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        err?.message ||
        "Failed to submit leave request. Please check the details and try again.";
      setSubmitError(typeof msg === "string" ? msg : JSON.stringify(msg));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleApprove(l: LeaveRequest) { await approveLeave(l.id, user?.employeeId || user?.id || ""); load(); }
  async function handleReject(l: LeaveRequest) { await rejectLeave(l.id, user?.employeeId || user?.id || ""); load(); }
  async function handleCancel(l: LeaveRequest) { await cancelLeave(l.id); load(); }

  const columns: Column<LeaveRequest>[] = [
    {
      key: "employee",
      header: "Employee",
      sortValue: (l) => getEmployeeName(l.employeeId || (l as any).employee_id),
      render: (l) => <span className="font-medium text-text">{getEmployeeName(l.employeeId || (l as any).employee_id)}</span>,
    },
    { key: "type", header: "Leave Type", render: (l) => l.leaveType || (l as any).leave_type },
    { key: "dates", header: "Dates", sortValue: (l) => l.startDate, render: (l) => `${formatDate(l.startDate || (l as any).start_date)} \u2013 ${formatDate(l.endDate || (l as any).end_date)}` },
    { key: "days", header: "Days", sortValue: (l) => l.totalDays, render: (l) => l.totalDays ?? (l as any).total_days },
    { key: "reason", header: "Reason", render: (l) => <span className="text-text-muted line-clamp-1 max-w-[180px] block">{l.reason}</span> },
    { key: "applied", header: "Applied", sortValue: (l) => l.appliedDate, render: (l) => formatDate(l.appliedDate || (l as any).applied_date) },
    { key: "status", header: "Status", render: (l) => <StatusBadge status={l.status} /> },
    { key: "actions", header: "Actions", render: (l) => (
      <div className="flex items-center gap-1">
        {l.status === "Pending" && can("leave.approve") && (
          <Button variant="ghost" size="icon" onClick={() => handleApprove(l)} aria-label="Approve"><Check className="h-4 w-4 text-success" /></Button>
        )}
        {l.status === "Pending" && can("leave.reject") && (
          <Button variant="ghost" size="icon" onClick={() => handleReject(l)} aria-label="Reject"><X className="h-4 w-4 text-danger" /></Button>
        )}
        {l.status === "Pending" && (l.employeeId === user?.employeeId || (l as any).employee_id === user?.employeeId) && (
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

      {balancesError ? (
        <div className="mb-6 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
          Unable to load live leave balances.
        </div>
      ) : balances.length > 0 ? (
        <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-3">
          {balances.map((b, idx) => {
            const lType = b.leaveType || (b as any).leave_type || `Leave ${idx + 1}`;
            const empKey = b.employeeId || (b as any).employee_id || user?.employeeId || "emp";
            return (
              <Card key={`${empKey}-${lType}-${idx}`}>
                <CardContent className="py-4 text-center">
                  <p className="text-2xl font-semibold text-text">{b.balance}</p>
                  <p className="text-xs text-text-muted">{lType} days remaining</p>
                </CardContent>
              </Card>
            );
          })}
        </div>
      ) : null}

      <FilterBar>
        <SearchBar value={search} onChange={setSearch} placeholder="Search by employee" className="w-full sm:w-64" />
        {can("leave.view.all") && (
          <Select value={employeeFilter} onChange={(e) => setEmployeeFilter(e.target.value)} className="w-full sm:w-48">
            <option value="all">All Employees</option>
            {employeesList.map((e) => (
              <option key={e.id} value={e.id}>
                {e.firstName} {e.lastName} ({e.employeeCode})
              </option>
            ))}
          </Select>
        )}
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
        open={formOpen}
        onClose={() => {
          if (!submitting) {
            setFormOpen(false);
            setSubmitError(null);
          }
        }}
        title="Apply for Leave"
        size="md"
        footer={
          <>
            <Button
              variant="outline"
              onClick={() => {
                setFormOpen(false);
                setSubmitError(null);
              }}
              disabled={submitting}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              form="leave-apply-form"
              loading={submitting}
              disabled={submitting}
            >
              Submit Request
            </Button>
          </>
        }
      >
        <form id="leave-apply-form" className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
          {submitError && (
            <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700" role="alert">
              {submitError}
            </div>
          )}

          {Object.keys(errors).length > 0 && (
            <div className="rounded-md border border-red-200 bg-red-50 p-2.5 text-xs text-red-700" role="alert">
              {errors.employeeId?.message ||
                errors.startDate?.message ||
                errors.endDate?.message ||
                errors.reason?.message ||
                "Please correct the errors in the form before submitting."}
            </div>
          )}

          {can("leave.view.all") && (
            <div>
              <Label required>Employee</Label>
              <Select {...register("employeeId")} error={!!errors.employeeId}>
                <option value="">{employeesList.length === 0 ? "No employees available" : "Select employee"}</option>
                {employeesList.map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.firstName} {e.lastName} ({e.employeeCode})
                  </option>
                ))}
              </Select>
              {errors.employeeId && <p className="mt-1 text-xs text-danger">{errors.employeeId.message}</p>}
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
            <div>
              <Label required>Start Date</Label>
              <Input type="date" {...register("startDate")} error={!!errors.startDate} />
              {errors.startDate && <p className="mt-1 text-xs text-danger">{errors.startDate.message}</p>}
            </div>
            <div>
              <Label required>End Date</Label>
              <Input type="date" {...register("endDate")} error={!!errors.endDate} />
              {errors.endDate && <p className="mt-1 text-xs text-danger">{errors.endDate.message}</p>}
            </div>
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
