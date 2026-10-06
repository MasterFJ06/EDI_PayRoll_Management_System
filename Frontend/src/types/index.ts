// ---------------------------------------------------------------------------
// Core domain types. These mirror the Pydantic response models the FastAPI
// backend is expected to return, so services can be swapped from mock -> HTTP
// without changing consumers.
// ---------------------------------------------------------------------------

export type Role =
  | "Employee"
  | "Manager"
  | "HR"
  | "Payroll Administrator"
  | "System Administrator"
  | "Management";

export type Permission =
  | "employee.view.self" | "employee.view.all" | "employee.create" | "employee.update" | "employee.delete"
  | "attendance.view.self" | "attendance.view.all" | "attendance.create" | "attendance.update"
  | "leave.apply" | "leave.view.self" | "leave.view.all" | "leave.approve" | "leave.reject"
  | "salary.view.self" | "salary.view.all" | "salary.create" | "salary.update"
  | "payroll.view" | "payroll.process" | "payroll.approve" | "payroll.validate"
  | "payslip.view.self" | "payslip.view.all" | "payslip.generate"
  | "reports.view" | "reports.export"
  | "audit.view"
  | "backup.create" | "backup.restore"
  | "monitoring.view"
  | "users.manage" | "roles.manage" | "org.manage";

export interface AppUser {
  id: string;
  username: string;
  firstName: string;
  lastName: string;
  email: string;
  phone: string;
  employeeId: string | null;
  role: Role;
  status: "Active" | "Inactive";
  avatarColor: string;
}

export interface Department {
  id: string;
  code: string;
  name: string;
  description: string;
  headEmployeeId: string | null;
  headName: string | null;
  status: "Active" | "Inactive";
  employeeCount: number;
  createdDate: string;
  updatedDate: string;
}

export interface Designation {
  id: string;
  code: string;
  name: string;
  description: string;
  hierarchyLevel: number;
  departmentId: string;
  status: "Active" | "Inactive";
  createdDate: string;
  updatedDate: string;
}

export type EmploymentType = "Full-Time" | "Part-Time" | "Contract" | "Intern";
export type EmploymentStatus = "Active" | "On Leave" | "Suspended" | "Terminated";

export interface Employee {
  id: string;
  employeeCode: string;
  firstName: string;
  lastName: string;
  email: string;
  phone: string;
  dateOfBirth: string;
  gender: "Male" | "Female" | "Other";
  departmentId: string;
  designationId: string;
  managerId: string | null;
  employmentType: EmploymentType;
  joiningDate: string;
  employmentStatus: EmploymentStatus;
  address: string;
  emergencyContact: string;
  createdDate: string;
  updatedDate: string;
}

export type AttendanceStatus = "Present" | "Absent" | "Late" | "Half-Day" | "Holiday";

export interface AttendanceRecord {
  id: string;
  employeeId: string;
  attendanceDate: string;
  checkIn: string | null;
  checkOut: string | null;
  workingHours: number;
  overtimeHours: number;
  status: AttendanceStatus;
  remarks: string;
  createdAt: string;
  updatedAt: string;
}

export type LeaveType = "Casual" | "Sick" | "Earned" | "Maternity" | "Paternity" | "Unpaid";
export type LeaveApprovalStatus = "Pending" | "Approved" | "Rejected" | "Cancelled";

export interface LeaveRequest {
  id: string;
  employeeId: string;
  leaveType: LeaveType;
  startDate: string;
  endDate: string;
  totalDays: number;
  reason: string;
  status: LeaveApprovalStatus;
  approverId: string | null;
  appliedDate: string;
  approvalDate: string | null;
}

export interface LeaveBalance {
  employeeId: string;
  leaveType: LeaveType;
  entitled: number;
  used: number;
  balance: number;
}

export interface SalaryStructure {
  id: string;
  employeeId: string;
  basic: number;
  hra: number;
  da: number;
  specialAllowance: number;
  travelAllowance: number;
  medicalAllowance: number;
  otherAllowances: number;
  providentFund: number;
  professionalTax: number;
  bonus: number;
  overtimeRate: number;
  esi: number;
  incomeTax: number;
  insurance: number;
  loanDeduction: number;
  otherDeductions: number;
  effectiveFrom: string;
  effectiveTo: string | null;
  revisionNumber: number;
  status: "Active" | "Superseded" | "Draft";
}

export type PayrollStatus = "Draft" | "Validated" | "Processed" | "Approved" | "Paid";

export interface PayrollRecord {
  id: string;
  payrollMonth: string;
  employeeId: string;
  basicSalary: number;
  allowances: number;
  overtime: number;
  leaveDeductions: number;
  tax: number;
  otherDeductions: number;
  grossSalary: number;
  totalDeductions: number;
  netSalary: number;
  status: PayrollStatus;
  generatedDate: string;
  generatedBy: string;
}

export type DeductionType = "PF" | "ESI" | "Professional Tax" | "Income Tax" | "Insurance" | "Loan" | "Other";

export interface Deduction {
  id: string;
  employeeId: string;
  payrollId: string;
  type: DeductionType;
  calculationMethod: "Percentage" | "Flat" | "Slab";
  amount: number;
  ruleApplied: string;
  effectiveDate: string;
  status: "Active" | "Inactive";
}

export type ValidationSeverity = "Information" | "Warning" | "Error" | "Critical";

export interface PayrollValidationIssue {
  id: string;
  employeeId: string;
  validationType: string;
  status: "Open" | "Resolved";
  message: string;
  severity: ValidationSeverity;
  timestamp: string;
  validatedBy: string;
}

export interface Payslip {
  id: string;
  payrollId: string;
  employeeId: string;
  payrollMonth: string;
  basicSalary: number;
  allowances: number;
  deductions: number;
  grossSalary: number;
  netSalary: number;
  generatedDate: string;
  digitalSignature: string;
  status: "Generated" | "Sent" | "Downloaded";
}

export interface LeaveAlert {
  id: string;
  employeeId: string;
  leaveType: LeaveType;
  currentBalance: number;
  threshold: number;
  alertType: "Normal" | "Warning" | "Critical";
  message: string;
  createdDate: string;
  readStatus: boolean;
}

export interface ReportExport {
  id: string;
  reportId: string;
  reportType: string;
  format: "PDF" | "Excel" | "CSV";
  requestedBy: string;
  fileName: string;
  timestamp: string;
  status: "Completed" | "Processing" | "Failed";
  downloadLocation: string;
  fileSize: string;
}

export interface AuditLog {
  id: string;
  timestamp: string;
  userId: string;
  userName: string;
  role: Role;
  module: string;
  action: string;
  affectedRecord: string;
  oldValue: Record<string, unknown> | null;
  newValue: Record<string, unknown> | null;
  ipAddress: string;
  status: "Success" | "Failed";
  remarks: string;
}

export interface Backup {
  id: string;
  type: "Full" | "Incremental" | "Differential";
  timestamp: string;
  size: string;
  location: string;
  createdBy: string;
  status: "Completed" | "In Progress" | "Failed";
  restoreStatus: "N/A" | "Restored" | "Failed";
  checksum: string;
  remarks: string;
}

export interface SystemMonitor {
  id: string;
  component: string;
  serviceStatus: "Online" | "Degraded" | "Offline";
  cpuUsage: number;
  memoryUsage: number;
  databaseStatus: "Connected" | "Disconnected";
  responseTimeMs: number;
  healthStatus: "Healthy" | "Warning" | "Critical";
  timestamp: string;
  alertStatus: "None" | "Alert";
}

export interface AppNotification {
  id: string;
  category: "Payroll" | "Leave" | "Attendance" | "Security" | "Employee" | "System";
  message: string;
  timestamp: string;
  read: boolean;
}
