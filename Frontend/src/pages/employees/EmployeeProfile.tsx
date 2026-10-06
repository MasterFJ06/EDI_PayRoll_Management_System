import { useEffect, useState, type ReactNode } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Mail, Phone, MapPin, Calendar, Briefcase } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { Card, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { EmployeeAvatar } from "@/components/common/EmployeeAvatar";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Tabs } from "@/components/ui/Tabs";
import { LoadingState } from "@/components/common/LoadingState";
import { EmptyState } from "@/components/common/EmptyState";
import { getEmployee } from "@/services/employeeService";
import {
  departmentName, designationName, employeeName, attendanceRecords, leaveRequests,
  leaveBalances, salaryStructures, payslips,
} from "@/data/mockData";
import { formatDate, formatINR, monthLabel } from "@/utils/format";
import type { Employee } from "@/types";

export default function EmployeeProfile() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [employee, setEmployee] = useState<Employee | null | undefined>(undefined);

  useEffect(() => {
    if (!id) return;
    getEmployee(id).then((e) => setEmployee(e ?? null));
  }, [id]);

  if (employee === undefined) return <LoadingState label="Loading employee profile..." />;
  if (employee === null) return <EmptyState title="Employee not found" description="This employee record may have been removed." />;

  const myAttendance = attendanceRecords.filter((a) => a.employeeId === employee.id);
  const myLeaves = leaveRequests.filter((l) => l.employeeId === employee.id);
  const myBalances = leaveBalances.filter((b) => b.employeeId === employee.id);
  const structure = salaryStructures.find((s) => s.employeeId === employee.id);
  const myPayslips = payslips.filter((p) => p.employeeId === employee.id);

  return (
    <div>
      <button onClick={() => navigate(-1)} className="mb-4 flex items-center gap-1.5 text-sm text-text-muted hover:text-text">
        <ArrowLeft className="h-4 w-4" /> Back to Directory
      </button>

      <Card className="mb-6">
        <CardContent>
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-4">
              <EmployeeAvatar firstName={employee.firstName} lastName={employee.lastName} size="lg" />
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="font-display text-xl font-semibold text-text">{employee.firstName} {employee.lastName}</h1>
                  <StatusBadge status={employee.employmentStatus} />
                </div>
                <p className="text-sm text-text-muted">{designationName(employee.designationId)} \u00b7 {departmentName(employee.departmentId)}</p>
                <p className="text-xs text-text-muted mt-0.5">{employee.employeeCode}</p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-x-6 gap-y-1.5 text-sm sm:text-right">
              <span className="flex items-center gap-1.5 text-text-muted"><Mail className="h-3.5 w-3.5" /> {employee.email}</span>
              <span className="flex items-center gap-1.5 text-text-muted"><Phone className="h-3.5 w-3.5" /> {employee.phone}</span>
              <span className="flex items-center gap-1.5 text-text-muted"><Calendar className="h-3.5 w-3.5" /> Joined {formatDate(employee.joiningDate)}</span>
              <span className="flex items-center gap-1.5 text-text-muted"><Briefcase className="h-3.5 w-3.5" /> {employee.employmentType}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      <Tabs
        tabs={[
          { key: "personal", label: "Personal Information" },
          { key: "employment", label: "Employment Information" },
          { key: "attendance", label: "Attendance" },
          { key: "leave", label: "Leave" },
          { key: "salary", label: "Salary" },
          { key: "payslips", label: "Payslips" },
        ]}
      >
        {(active) => (
          <>
            {active === "personal" && (
              <Card><CardContent className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <Field label="Date of Birth" value={formatDate(employee.dateOfBirth)} />
                <Field label="Gender" value={employee.gender} />
                <Field label="Address" value={employee.address} icon={<MapPin className="h-3.5 w-3.5" />} />
                <Field label="Emergency Contact" value={employee.emergencyContact} />
              </CardContent></Card>
            )}
            {active === "employment" && (
              <Card><CardContent className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <Field label="Employee Code" value={employee.employeeCode} />
                <Field label="Department" value={departmentName(employee.departmentId)} />
                <Field label="Designation" value={designationName(employee.designationId)} />
                <Field label="Manager" value={employeeName(employee.managerId)} />
                <Field label="Employment Type" value={employee.employmentType} />
                <Field label="Joining Date" value={formatDate(employee.joiningDate)} />
                <Field label="Employment Status" value={employee.employmentStatus} />
                <Field label="Last Updated" value={formatDate(employee.updatedDate)} />
              </CardContent></Card>
            )}
            {active === "attendance" && (
              <Card><CardContent>
                {myAttendance.length === 0 ? <EmptyState title="No attendance records" /> : (
                  <div className="space-y-2">
                    {myAttendance.map((a) => (
                      <div key={a.id} className="flex items-center justify-between rounded-lg border border-border px-3 py-2.5 text-sm">
                        <span className="text-text">{formatDate(a.attendanceDate)}</span>
                        <span className="text-text-muted">{a.checkIn ?? "\u2014"} \u2013 {a.checkOut ?? "\u2014"}</span>
                        <span className="text-text-muted">{a.workingHours}h</span>
                        <StatusBadge status={a.status} />
                      </div>
                    ))}
                  </div>
                )}
              </CardContent></Card>
            )}
            {active === "leave" && (
              <div className="space-y-4">
                <Card><CardContent>
                  <p className="mb-3 text-sm font-semibold text-text">Leave Balances</p>
                  <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                    {myBalances.map((b) => (
                      <div key={b.leaveType} className="rounded-lg border border-border p-3 text-center">
                        <p className="text-lg font-semibold text-text">{b.balance}</p>
                        <p className="text-xs text-text-muted">{b.leaveType} days left</p>
                      </div>
                    ))}
                  </div>
                </CardContent></Card>
                <Card><CardContent>
                  <p className="mb-3 text-sm font-semibold text-text">Leave History</p>
                  {myLeaves.length === 0 ? <EmptyState title="No leave history" /> : (
                    <div className="space-y-2">
                      {myLeaves.map((l) => (
                        <div key={l.id} className="flex items-center justify-between rounded-lg border border-border px-3 py-2.5 text-sm">
                          <span className="text-text">{l.leaveType}</span>
                          <span className="text-text-muted">{formatDate(l.startDate)} \u2013 {formatDate(l.endDate)}</span>
                          <StatusBadge status={l.status} />
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent></Card>
              </div>
            )}
            {active === "salary" && (
              <Card><CardContent>
                {!structure ? <EmptyState title="No salary structure assigned" /> : (
                  <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                    <div>
                      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-text-muted">Earnings</p>
                      <Row label="Basic Salary" value={structure.basic} />
                      <Row label="HRA" value={structure.hra} />
                      <Row label="DA" value={structure.da} />
                      <Row label="Special Allowance" value={structure.specialAllowance} />
                      <Row label="Travel Allowance" value={structure.travelAllowance} />
                      <Row label="Medical Allowance" value={structure.medicalAllowance} />
                    </div>
                    <div>
                      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-text-muted">Deductions</p>
                      <Row label="Provident Fund" value={structure.providentFund} />
                      <Row label="ESI" value={structure.esi} />
                      <Row label="Professional Tax" value={structure.professionalTax} />
                      <Row label="Income Tax" value={structure.incomeTax} />
                      <Row label="Insurance" value={structure.insurance} />
                    </div>
                  </div>
                )}
              </CardContent></Card>
            )}
            {active === "payslips" && (
              <Card><CardContent>
                {myPayslips.length === 0 ? <EmptyState title="No payslips generated yet" /> : (
                  <div className="space-y-2">
                    {myPayslips.map((p) => (
                      <div key={p.id} className="flex items-center justify-between rounded-lg border border-border px-3 py-2.5 text-sm">
                        <span className="text-text font-medium">{monthLabel(p.payrollMonth)}</span>
                        <span className="text-text-muted">Net: {formatINR(p.netSalary)}</span>
                        <Button variant="outline" size="sm">Download</Button>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent></Card>
            )}
          </>
        )}
      </Tabs>
    </div>
  );
}

function Field({ label, value, icon }: { label: string; value: string; icon?: ReactNode }) {
  return (
    <div>
      <p className="text-xs font-medium text-text-muted">{label}</p>
      <p className="mt-1 flex items-center gap-1.5 text-sm text-text">{icon}{value}</p>
    </div>
  );
}
function Row({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex justify-between border-b border-border py-1.5 text-sm last:border-0">
      <span className="text-text-muted">{label}</span>
      <span className="font-medium text-text">{formatINR(value)}</span>
    </div>
  );
}
