import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { CalendarCheck, Plus, Clock, Users, UserX, Timer, Sun } from "lucide-react";
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
import { DashboardCard } from "@/components/common/DashboardCard";
import { DataTable, type Column } from "@/components/tables/DataTable";
import { ErrorState } from "@/components/common/ErrorState";
import { listAttendance, createAttendance } from "@/services/attendanceService";
import { employees, employeeName } from "@/data/mockData";
import { formatDate } from "@/utils/format";
import { useAuth } from "@/context/AuthContext";
import type { AttendanceRecord, AttendanceStatus } from "@/types";

const schema = z.object({
  employeeId: z.string().min(1, "Employee is required"),
  attendanceDate: z.string().min(1, "Date is required"),
  checkIn: z.string().optional(),
  checkOut: z.string().optional(),
  status: z.enum(["Present", "Absent", "Late", "Half-Day", "Holiday"]),
  remarks: z.string().optional(),
});
type FormValues = z.infer<typeof schema>;

export default function Attendance() {
  const { can } = useAuth();
  const [items, setItems] = useState<AttendanceRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [dateFilter, setDateFilter] = useState("all");
  const [formOpen, setFormOpen] = useState(false);

  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { status: "Present", attendanceDate: "2026-08-11" },
  });

  async function load() {
    setLoading(true); setError(false);
    try { setItems(await listAttendance()); } catch { setError(true); } finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []);

  const dates = Array.from(new Set(items.map((a) => a.attendanceDate))).sort().reverse();

  const filtered = items.filter((a) => {
    const matchSearch = employeeName(a.employeeId).toLowerCase().includes(search.toLowerCase());
    const matchStatus = statusFilter === "all" || a.status === statusFilter;
    const matchDate = dateFilter === "all" || a.attendanceDate === dateFilter;
    return matchSearch && matchStatus && matchDate;
  });

  const counts = (["Present", "Absent", "Late", "Half-Day", "Holiday"] as AttendanceStatus[]).map((s) => ({
    status: s, count: items.filter((a) => a.status === s).length,
  }));
  const totalOvertime = items.reduce((s, a) => s + a.overtimeHours, 0);

  async function onSubmit(values: FormValues) {
    await createAttendance({
      id: `ATT${Date.now()}`, ...values, checkIn: values.checkIn || null, checkOut: values.checkOut || null,
      workingHours: values.status === "Absent" ? 0 : values.status === "Half-Day" ? 4 : 8.3,
      overtimeHours: 0, remarks: values.remarks ?? "",
      createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(),
    });
    setFormOpen(false);
    load();
  }

  const columns: Column<AttendanceRecord>[] = [
    { key: "employee", header: "Employee", sortValue: (a) => employeeName(a.employeeId), render: (a) => <span className="font-medium text-text">{employeeName(a.employeeId)}</span> },
    { key: "date", header: "Date", sortValue: (a) => a.attendanceDate, render: (a) => formatDate(a.attendanceDate) },
    { key: "checkin", header: "Check-In", render: (a) => a.checkIn ?? "\u2014" },
    { key: "checkout", header: "Check-Out", render: (a) => a.checkOut ?? "\u2014" },
    { key: "hours", header: "Working Hours", sortValue: (a) => a.workingHours, render: (a) => `${a.workingHours}h` },
    { key: "overtime", header: "Overtime", sortValue: (a) => a.overtimeHours, render: (a) => a.overtimeHours ? `${a.overtimeHours}h` : "\u2014" },
    { key: "status", header: "Status", render: (a) => <StatusBadge status={a.status} /> },
  ];

  return (
    <div>
      <PageHeader
        title="Attendance Management"
        description="Daily check-ins, working hours and attendance status across the organization."
        icon={<CalendarCheck className="h-5 w-5" />}
        actions={can("attendance.create") ? <Button onClick={() => setFormOpen(true)}><Plus className="h-4 w-4" /> Mark Attendance</Button> : undefined}
      />

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6 mb-6">
        <DashboardCard label="Present" value={String(counts[0].count)} icon={<Users className="h-[18px] w-[18px]" />} tone="success" />
        <DashboardCard label="Absent" value={String(counts[1].count)} icon={<UserX className="h-[18px] w-[18px]" />} tone="danger" />
        <DashboardCard label="Late" value={String(counts[2].count)} icon={<Clock className="h-[18px] w-[18px]" />} tone="warning" />
        <DashboardCard label="Half-Day" value={String(counts[3].count)} icon={<Timer className="h-[18px] w-[18px]" />} tone="info" />
        <DashboardCard label="Holiday" value={String(counts[4].count)} icon={<Sun className="h-[18px] w-[18px]" />} tone="neutral" />
        <DashboardCard label="Overtime Hours" value={`${totalOvertime.toFixed(1)}h`} icon={<Clock className="h-[18px] w-[18px]" />} tone="primary" />
      </div>

      <FilterBar>
        <SearchBar value={search} onChange={setSearch} placeholder="Search by employee" className="w-full sm:w-64" />
        <Select value={dateFilter} onChange={(e) => setDateFilter(e.target.value)} className="w-full sm:w-44">
          <option value="all">All Dates</option>
          {dates.map((d) => <option key={d} value={d}>{formatDate(d)}</option>)}
        </Select>
        <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="w-full sm:w-40">
          <option value="all">All Status</option>
          <option>Present</option><option>Absent</option><option>Late</option><option>Half-Day</option><option>Holiday</option>
        </Select>
      </FilterBar>

      <div className="mt-4">
        {error ? <ErrorState onRetry={load} /> : (
          <DataTable columns={columns} data={filtered} rowKey={(a) => a.id} loading={loading} pageSize={8} emptyTitle="No attendance records found" />
        )}
      </div>

      <Dialog
        open={formOpen} onClose={() => setFormOpen(false)} title="Mark Attendance" size="md"
        footer={<>
          <Button variant="outline" onClick={() => setFormOpen(false)}>Cancel</Button>
          <Button onClick={handleSubmit(onSubmit)} loading={isSubmitting}>Save Attendance</Button>
        </>}
      >
        <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
          <div>
            <Label required>Employee</Label>
            <Select {...register("employeeId")} error={!!errors.employeeId}>
              <option value="">Select employee</option>
              {employees.map((e) => <option key={e.id} value={e.id}>{e.firstName} {e.lastName} ({e.employeeCode})</option>)}
            </Select>
            {errors.employeeId && <p className="mt-1 text-xs text-danger">{errors.employeeId.message}</p>}
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div><Label required>Date</Label><Input type="date" {...register("attendanceDate")} /></div>
            <div><Label required>Status</Label><Select {...register("status")}><option>Present</option><option>Absent</option><option>Late</option><option>Half-Day</option><option>Holiday</option></Select></div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div><Label>Check-In Time</Label><Input type="time" {...register("checkIn")} /></div>
            <div><Label>Check-Out Time</Label><Input type="time" {...register("checkOut")} /></div>
          </div>
          <div><Label>Remarks</Label><Textarea rows={2} {...register("remarks")} placeholder="Optional notes" /></div>
        </form>
      </Dialog>
    </div>
  );
}
