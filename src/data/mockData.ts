import type {
  AppUser, Department, Designation, Employee, AttendanceRecord, LeaveRequest, LeaveBalance,
  SalaryStructure, PayrollRecord, Deduction, PayrollValidationIssue, Payslip, LeaveAlert,
  ReportExport, AuditLog, Backup, SystemMonitor, AppNotification,
} from "@/types";

export const departments: Department[] = [
  { id: "D01", code: "IT", name: "Information Technology", description: "Software engineering, infrastructure and IT support.", headEmployeeId: "EMP004", headName: "Amit Kulkarni", status: "Active", employeeCount: 42, createdDate: "2019-04-01", updatedDate: "2025-11-12" },
  { id: "D02", code: "HR", name: "Human Resources", description: "Talent acquisition, employee relations and payroll administration.", headEmployeeId: "EMP003", headName: "Priya Sharma", status: "Active", employeeCount: 11, createdDate: "2019-04-01", updatedDate: "2025-09-02" },
  { id: "D03", code: "FIN", name: "Finance", description: "Accounting, budgeting, and financial reporting.", headEmployeeId: "EMP002", headName: "Rahul Patil", status: "Active", employeeCount: 18, createdDate: "2019-04-01", updatedDate: "2025-08-20" },
  { id: "D04", code: "SALES", name: "Sales", description: "Business development and client accounts.", headEmployeeId: "EMP005", headName: "Sneha Joshi", status: "Active", employeeCount: 27, createdDate: "2019-06-15", updatedDate: "2025-07-01" },
  { id: "D05", code: "OPS", name: "Operations", description: "Facilities, logistics and vendor management.", headEmployeeId: null, headName: null, status: "Active", employeeCount: 14, createdDate: "2020-01-10", updatedDate: "2025-05-18" },
];

export const designations: Designation[] = [
  { id: "DS01", code: "SE", name: "Software Engineer", description: "Builds and maintains product features.", hierarchyLevel: 3, departmentId: "D01", status: "Active", createdDate: "2019-04-01", updatedDate: "2024-01-10" },
  { id: "DS02", code: "SSE", name: "Senior Software Engineer", description: "Leads feature delivery and mentors engineers.", hierarchyLevel: 4, departmentId: "D01", status: "Active", createdDate: "2019-04-01", updatedDate: "2024-01-10" },
  { id: "DS03", code: "PM", name: "Project Manager", description: "Owns delivery timelines and stakeholder communication.", hierarchyLevel: 5, departmentId: "D01", status: "Active", createdDate: "2019-04-01", updatedDate: "2024-01-10" },
  { id: "DS04", code: "ACC", name: "Accountant", description: "Manages ledgers, invoices and reconciliations.", hierarchyLevel: 3, departmentId: "D03", status: "Active", createdDate: "2019-04-01", updatedDate: "2023-11-02" },
  { id: "DS05", code: "HRE", name: "HR Executive", description: "Handles recruitment and employee lifecycle.", hierarchyLevel: 3, departmentId: "D02", status: "Active", createdDate: "2019-04-01", updatedDate: "2023-11-02" },
  { id: "DS06", code: "SE-X", name: "Sales Executive", description: "Manages client accounts and revenue targets.", hierarchyLevel: 3, departmentId: "D04", status: "Active", createdDate: "2019-06-15", updatedDate: "2023-06-01" },
  { id: "DS07", code: "OPX", name: "Operations Executive", description: "Coordinates facilities and vendor operations.", hierarchyLevel: 3, departmentId: "D05", status: "Active", createdDate: "2020-01-10", updatedDate: "2023-06-01" },
];

export const employees: Employee[] = [
  { id: "EMP001", employeeCode: "EMP001", firstName: "Radhika", lastName: "Suryatal", email: "radhika.suryatal@company.in", phone: "+91 98230 11223", dateOfBirth: "1997-03-14", gender: "Female", departmentId: "D01", designationId: "DS01", managerId: "EMP004", employmentType: "Full-Time", joiningDate: "2022-07-04", employmentStatus: "Active", address: "Baner, Pune, MH", emergencyContact: "+91 98220 99887", createdDate: "2022-07-04", updatedDate: "2025-10-01" },
  { id: "EMP002", employeeCode: "EMP002", firstName: "Rahul", lastName: "Patil", email: "rahul.patil@company.in", phone: "+91 99870 44556", dateOfBirth: "1990-11-02", gender: "Male", departmentId: "D03", designationId: "DS04", managerId: null, employmentType: "Full-Time", joiningDate: "2019-08-19", employmentStatus: "Active", address: "Kothrud, Pune, MH", emergencyContact: "+91 99231 22110", createdDate: "2019-08-19", updatedDate: "2025-06-14" },
  { id: "EMP003", employeeCode: "EMP003", firstName: "Priya", lastName: "Sharma", email: "priya.sharma@company.in", phone: "+91 98765 33221", dateOfBirth: "1993-05-27", gender: "Female", departmentId: "D02", designationId: "DS05", managerId: null, employmentType: "Full-Time", joiningDate: "2020-02-11", employmentStatus: "Active", address: "Viman Nagar, Pune, MH", emergencyContact: "+91 98450 11002", createdDate: "2020-02-11", updatedDate: "2025-04-22" },
  { id: "EMP004", employeeCode: "EMP004", firstName: "Amit", lastName: "Kulkarni", email: "amit.kulkarni@company.in", phone: "+91 97620 88991", dateOfBirth: "1988-01-19", gender: "Male", departmentId: "D01", designationId: "DS03", managerId: null, employmentType: "Full-Time", joiningDate: "2018-03-05", employmentStatus: "Active", address: "Hinjawadi, Pune, MH", emergencyContact: "+91 97400 55221", createdDate: "2018-03-05", updatedDate: "2025-01-30" },
  { id: "EMP005", employeeCode: "EMP005", firstName: "Sneha", lastName: "Joshi", email: "sneha.joshi@company.in", phone: "+91 96650 77332", dateOfBirth: "1995-09-08", gender: "Female", departmentId: "D04", designationId: "DS06", managerId: null, employmentType: "Full-Time", joiningDate: "2021-11-22", employmentStatus: "Active", address: "Wakad, Pune, MH", emergencyContact: "+91 96540 11223", createdDate: "2021-11-22", updatedDate: "2025-05-10" },
  { id: "EMP006", employeeCode: "EMP006", firstName: "Karan", lastName: "Deshmukh", email: "karan.deshmukh@company.in", phone: "+91 90210 44112", dateOfBirth: "1996-06-30", gender: "Male", departmentId: "D01", designationId: "DS02", managerId: "EMP004", employmentType: "Full-Time", joiningDate: "2020-09-14", employmentStatus: "Active", address: "Aundh, Pune, MH", emergencyContact: "+91 90330 22114", createdDate: "2020-09-14", updatedDate: "2025-03-11" },
  { id: "EMP007", employeeCode: "EMP007", firstName: "Neha", lastName: "Kadam", email: "neha.kadam@company.in", phone: "+91 91234 66778", dateOfBirth: "1998-12-05", gender: "Female", departmentId: "D01", designationId: "DS01", managerId: "EMP004", employmentType: "Full-Time", joiningDate: "2023-01-16", employmentStatus: "On Leave", address: "Pimpri, Pune, MH", emergencyContact: "+91 91009 33445", createdDate: "2023-01-16", updatedDate: "2025-09-20" },
  { id: "EMP008", employeeCode: "EMP008", firstName: "Vikram", lastName: "Rane", email: "vikram.rane@company.in", phone: "+91 89991 22335", dateOfBirth: "1992-04-21", gender: "Male", departmentId: "D05", designationId: "DS07", managerId: null, employmentType: "Contract", joiningDate: "2024-02-01", employmentStatus: "Active", address: "Katraj, Pune, MH", emergencyContact: "+91 89760 44112", createdDate: "2024-02-01", updatedDate: "2025-02-01" },
  { id: "EMP009", employeeCode: "EMP009", firstName: "Ananya", lastName: "Iyer", email: "ananya.iyer@company.in", phone: "+91 93456 88221", dateOfBirth: "1999-08-17", gender: "Female", departmentId: "D04", designationId: "DS06", managerId: "EMP005", employmentType: "Full-Time", joiningDate: "2023-06-05", employmentStatus: "Active", address: "Kharadi, Pune, MH", emergencyContact: "+91 93222 11009", createdDate: "2023-06-05", updatedDate: "2025-06-01" },
  { id: "EMP010", employeeCode: "EMP010", firstName: "Suresh", lastName: "Naik", email: "suresh.naik@company.in", phone: "+91 88990 11224", dateOfBirth: "1985-10-11", gender: "Male", departmentId: "D03", designationId: "DS04", managerId: "EMP002", employmentType: "Part-Time", joiningDate: "2021-05-19", employmentStatus: "Suspended", address: "Shivajinagar, Pune, MH", emergencyContact: "+91 88110 55223", createdDate: "2021-05-19", updatedDate: "2025-07-15" },
];

// ---------------------------------------------------------------------------
// Application users (auth identities). Passwords are never stored/exposed —
// this is a frontend-only mock login for the prototype.
// ---------------------------------------------------------------------------
export const appUsers: AppUser[] = [
  { id: "U001", username: "radhika.suryatal", firstName: "Radhika", lastName: "Suryatal", email: "radhika.suryatal@company.in", phone: "+91 98230 11223", employeeId: "EMP001", role: "Employee", status: "Active", avatarColor: "bg-blue-500" },
  { id: "U002", username: "amit.kulkarni", firstName: "Amit", lastName: "Kulkarni", email: "amit.kulkarni@company.in", phone: "+91 97620 88991", employeeId: "EMP004", role: "Manager", status: "Active", avatarColor: "bg-indigo-500" },
  { id: "U003", username: "priya.sharma", firstName: "Priya", lastName: "Sharma", email: "priya.sharma@company.in", phone: "+91 98765 33221", employeeId: "EMP003", role: "HR", status: "Active", avatarColor: "bg-emerald-500" },
  { id: "U004", username: "payroll.admin", firstName: "Meera", lastName: "Kapoor", email: "meera.kapoor@company.in", phone: "+91 90000 12345", employeeId: null, role: "Payroll Administrator", status: "Active", avatarColor: "bg-amber-500" },
  { id: "U005", username: "sysadmin", firstName: "Rohan", lastName: "Verma", email: "rohan.verma@company.in", phone: "+91 90000 54321", employeeId: null, role: "System Administrator", status: "Active", avatarColor: "bg-slate-600" },
  { id: "U006", username: "management", firstName: "Anjali", lastName: "Mehta", email: "anjali.mehta@company.in", phone: "+91 90000 99887", employeeId: null, role: "Management", status: "Active", avatarColor: "bg-sky-600" },
];

function genAttendance(): AttendanceRecord[] {
  const statuses: AttendanceRecord["status"][] = ["Present", "Present", "Present", "Present", "Late", "Half-Day", "Absent"];
  const records: AttendanceRecord[] = [];
  let id = 1;
  const days = ["2026-08-03", "2026-08-04", "2026-08-05", "2026-08-06", "2026-08-07", "2026-08-10", "2026-08-11"];
  for (const emp of employees.slice(0, 8)) {
    days.forEach((date, i) => {
      const status = statuses[(i + emp.id.charCodeAt(3)) % statuses.length];
      const checkIn = status === "Absent" ? null : status === "Late" ? "10:12 AM" : "09:24 AM";
      const checkOut = status === "Absent" ? null : status === "Half-Day" ? "01:30 PM" : "06:42 PM";
      const workingHours = status === "Absent" ? 0 : status === "Half-Day" ? 4 : 8.3;
      records.push({
        id: `ATT${String(id++).padStart(4, "0")}`,
        employeeId: emp.id,
        attendanceDate: date,
        checkIn, checkOut, workingHours,
        overtimeHours: status === "Present" && i === 3 ? 1.5 : 0,
        status,
        remarks: status === "Late" ? "Traffic delay" : status === "Absent" ? "Informed sick" : "",
        createdAt: `${date}T09:30:00`,
        updatedAt: `${date}T19:00:00`,
      });
    });
  }
  return records;
}
export const attendanceRecords = genAttendance();

export const leaveRequests: LeaveRequest[] = [
  { id: "LV1001", employeeId: "EMP001", leaveType: "Casual", startDate: "2026-08-14", endDate: "2026-08-15", totalDays: 2, reason: "Family function", status: "Pending", approverId: "EMP004", appliedDate: "2026-08-08", approvalDate: null },
  { id: "LV1002", employeeId: "EMP007", leaveType: "Sick", startDate: "2026-08-01", endDate: "2026-08-09", totalDays: 7, reason: "Recovering from surgery", status: "Approved", approverId: "EMP004", appliedDate: "2026-07-30", approvalDate: "2026-07-31" },
  { id: "LV1003", employeeId: "EMP006", leaveType: "Earned", startDate: "2026-08-20", endDate: "2026-08-22", totalDays: 3, reason: "Personal travel", status: "Pending", approverId: "EMP004", appliedDate: "2026-08-09", approvalDate: null },
  { id: "LV1004", employeeId: "EMP009", leaveType: "Casual", startDate: "2026-07-18", endDate: "2026-07-18", totalDays: 1, reason: "Personal work", status: "Rejected", approverId: "EMP005", appliedDate: "2026-07-15", approvalDate: "2026-07-16" },
  { id: "LV1005", employeeId: "EMP002", leaveType: "Earned", startDate: "2026-09-01", endDate: "2026-09-05", totalDays: 5, reason: "Family vacation", status: "Approved", approverId: null, appliedDate: "2026-08-01", approvalDate: "2026-08-02" },
  { id: "LV1006", employeeId: "EMP001", leaveType: "Sick", startDate: "2026-06-10", endDate: "2026-06-11", totalDays: 2, reason: "Fever", status: "Approved", approverId: "EMP004", appliedDate: "2026-06-09", approvalDate: "2026-06-09" },
];

export const leaveBalances: LeaveBalance[] = [
  { employeeId: "EMP001", leaveType: "Casual", entitled: 12, used: 5, balance: 7 },
  { employeeId: "EMP001", leaveType: "Sick", entitled: 10, used: 2, balance: 8 },
  { employeeId: "EMP001", leaveType: "Earned", entitled: 15, used: 3, balance: 12 },
  { employeeId: "EMP007", leaveType: "Sick", entitled: 10, used: 9, balance: 1 },
  { employeeId: "EMP007", leaveType: "Casual", entitled: 12, used: 4, balance: 8 },
  { employeeId: "EMP006", leaveType: "Earned", entitled: 15, used: 13, balance: 2 },
];

function structureFor(empId: string, basic: number): SalaryStructure {
  const hra = Math.round(basic * 0.4);
  const da = Math.round(basic * 0.1);
  return {
    id: `SS-${empId}`, employeeId: empId, basic, hra, da,
    specialAllowance: Math.round(basic * 0.08),
    travelAllowance: 1600, medicalAllowance: 1250, otherAllowances: 500,
    providentFund: Math.round(basic * 0.12), professionalTax: 200,
    bonus: 0, overtimeRate: 350, esi: basic <= 21000 ? Math.round(basic * 0.0075) : 0,
    incomeTax: Math.round(basic * 0.04), insurance: 450, loanDeduction: 0, otherDeductions: 0,
    effectiveFrom: "2026-04-01", effectiveTo: null, revisionNumber: 2, status: "Active",
  };
}
export const salaryStructures: SalaryStructure[] = [
  structureFor("EMP001", 62000),
  structureFor("EMP002", 58000),
  structureFor("EMP003", 54000),
  structureFor("EMP004", 98000),
  structureFor("EMP005", 51000),
  structureFor("EMP006", 76000),
  structureFor("EMP007", 60000),
  structureFor("EMP008", 32000),
  structureFor("EMP009", 47000),
  structureFor("EMP010", 45000),
];

function computePayroll(ss: SalaryStructure, month: string, status: PayrollRecord["status"]): PayrollRecord {
  const allowances = ss.hra + ss.da + ss.specialAllowance + ss.travelAllowance + ss.medicalAllowance + ss.otherAllowances;
  const overtime = ss.overtimeRate * 2;
  const leaveDeductions = 0;
  const gross = ss.basic + allowances + ss.bonus + overtime;
  const totalDeductions = ss.providentFund + ss.esi + ss.professionalTax + ss.incomeTax + ss.insurance + ss.loanDeduction + ss.otherDeductions + leaveDeductions;
  const net = gross - totalDeductions;
  return {
    id: `PR-${month}-${ss.employeeId}`, payrollMonth: month, employeeId: ss.employeeId,
    basicSalary: ss.basic, allowances, overtime, leaveDeductions, tax: ss.incomeTax,
    otherDeductions: ss.otherDeductions, grossSalary: gross, totalDeductions, netSalary: net,
    status, generatedDate: "2026-08-01", generatedBy: "Meera Kapoor",
  };
}
export const payrollRecords: PayrollRecord[] = [
  ...salaryStructures.map((ss) => computePayroll(ss, "2026-07", "Paid")),
  ...salaryStructures.map((ss) => computePayroll(ss, "2026-08", "Draft")),
];

export const deductions: Deduction[] = salaryStructures.flatMap((ss) => ([
  { id: `DED-${ss.employeeId}-PF`, employeeId: ss.employeeId, payrollId: `PR-2026-08-${ss.employeeId}`, type: "PF", calculationMethod: "Percentage", amount: ss.providentFund, ruleApplied: "12% of Basic", effectiveDate: "2026-04-01", status: "Active" },
  { id: `DED-${ss.employeeId}-PT`, employeeId: ss.employeeId, payrollId: `PR-2026-08-${ss.employeeId}`, type: "Professional Tax", calculationMethod: "Flat", amount: ss.professionalTax, ruleApplied: "Maharashtra PT Slab", effectiveDate: "2026-04-01", status: "Active" },
  { id: `DED-${ss.employeeId}-IT`, employeeId: ss.employeeId, payrollId: `PR-2026-08-${ss.employeeId}`, type: "Income Tax", calculationMethod: "Slab", amount: ss.incomeTax, ruleApplied: "New Tax Regime FY26-27", effectiveDate: "2026-04-01", status: "Active" },
]));

export const payrollValidationIssues: PayrollValidationIssue[] = [
  { id: "VAL001", employeeId: "EMP008", validationType: "Missing Attendance", status: "Open", message: "Attendance not recorded for 3 working days in August 2026.", severity: "Warning", timestamp: "2026-08-10T09:15:00", validatedBy: "System" },
  { id: "VAL002", employeeId: "EMP010", validationType: "Invalid Employee Status", status: "Open", message: "Employee is Suspended but still included in payroll batch.", severity: "Critical", timestamp: "2026-08-10T09:15:00", validatedBy: "System" },
  { id: "VAL003", employeeId: "EMP007", validationType: "Leave Deduction Mismatch", status: "Open", message: "Unpaid leave days not reflected in leave deduction.", severity: "Error", timestamp: "2026-08-10T09:16:00", validatedBy: "System" },
  { id: "VAL004", employeeId: "EMP002", validationType: "Tax Calculation", status: "Resolved", message: "Income tax recalculated after investment declaration update.", severity: "Information", timestamp: "2026-08-09T14:02:00", validatedBy: "Meera Kapoor" },
];

export const payslips: Payslip[] = payrollRecords.filter(p => p.status === "Paid").map((p) => ({
  id: `PS-${p.payrollMonth}-${p.employeeId}`, payrollId: p.id, employeeId: p.employeeId, payrollMonth: p.payrollMonth,
  basicSalary: p.basicSalary, allowances: p.allowances, deductions: p.totalDeductions, grossSalary: p.grossSalary,
  netSalary: p.netSalary, generatedDate: "2026-08-01", digitalSignature: "Meera Kapoor (Payroll Admin)", status: "Generated",
}));

export const leaveAlerts: LeaveAlert[] = [
  { id: "AL001", employeeId: "EMP007", leaveType: "Sick", currentBalance: 1, threshold: 2, alertType: "Critical", message: "Sick leave balance critically low.", createdDate: "2026-08-09", readStatus: false },
  { id: "AL002", employeeId: "EMP006", leaveType: "Earned", currentBalance: 2, threshold: 3, alertType: "Warning", message: "Earned leave balance below recommended threshold.", createdDate: "2026-08-08", readStatus: false },
  { id: "AL003", employeeId: "EMP001", leaveType: "Casual", currentBalance: 7, threshold: 3, alertType: "Normal", message: "Casual leave balance is healthy.", createdDate: "2026-08-05", readStatus: true },
];

export const reportExports: ReportExport[] = [
  { id: "EXP001", reportId: "RPT-SAL-2026-07", reportType: "Salary Report", format: "PDF", requestedBy: "Meera Kapoor", fileName: "salary-report-jul-2026.pdf", timestamp: "2026-08-01T10:00:00", status: "Completed", downloadLocation: "/exports/salary-report-jul-2026.pdf", fileSize: "482 KB" },
  { id: "EXP002", reportId: "RPT-ATT-2026-07", reportType: "Attendance Summary", format: "Excel", requestedBy: "Priya Sharma", fileName: "attendance-summary-jul-2026.xlsx", timestamp: "2026-08-02T11:20:00", status: "Completed", downloadLocation: "/exports/attendance-jul-2026.xlsx", fileSize: "128 KB" },
  { id: "EXP003", reportId: "RPT-LEAVE-2026-07", reportType: "Leave Report", format: "CSV", requestedBy: "Priya Sharma", fileName: "leave-report-jul-2026.csv", timestamp: "2026-08-03T09:40:00", status: "Processing", downloadLocation: "", fileSize: "\u2014" },
];

export const auditLogs: AuditLog[] = [
  { id: "AUD1001", timestamp: "2026-08-10T09:12:44", userId: "U004", userName: "Meera Kapoor", role: "Payroll Administrator", module: "Payroll", action: "Payroll Processed", affectedRecord: "PR-2026-08-BATCH", oldValue: null, newValue: { status: "Processed", employees: 10 }, ipAddress: "10.20.4.12", status: "Success", remarks: "August 2026 payroll batch processed." },
  { id: "AUD1002", timestamp: "2026-08-09T16:45:02", userId: "U003", userName: "Priya Sharma", role: "HR", module: "Leave", action: "Leave Approved", affectedRecord: "LV1002", oldValue: { status: "Pending" }, newValue: { status: "Approved" }, ipAddress: "10.20.4.31", status: "Success", remarks: "" },
  { id: "AUD1003", timestamp: "2026-08-09T11:02:19", userId: "U003", userName: "Priya Sharma", role: "HR", module: "Employee", action: "Employee Updated", affectedRecord: "EMP007", oldValue: { employmentStatus: "Active" }, newValue: { employmentStatus: "On Leave" }, ipAddress: "10.20.4.31", status: "Success", remarks: "" },
  { id: "AUD1004", timestamp: "2026-08-08T18:22:51", userId: "U005", userName: "Rohan Verma", role: "System Administrator", module: "Infrastructure", action: "Backup Created", affectedRecord: "BKP-20260808", oldValue: null, newValue: { type: "Full", size: "1.8 GB" }, ipAddress: "10.20.4.02", status: "Success", remarks: "Scheduled nightly backup." },
  { id: "AUD1005", timestamp: "2026-08-07T13:11:08", userId: "U004", userName: "Meera Kapoor", role: "Payroll Administrator", module: "Salary", action: "Salary Updated", affectedRecord: "SS-EMP002", oldValue: { basic: 55000 }, newValue: { basic: 58000 }, ipAddress: "10.20.4.12", status: "Success", remarks: "Annual increment." },
  { id: "AUD1006", timestamp: "2026-08-06T08:55:37", userId: "U001", userName: "Radhika Suryatal", role: "Employee", module: "Auth", action: "Login", affectedRecord: "U001", oldValue: null, newValue: null, ipAddress: "182.71.44.9", status: "Success", remarks: "" },
  { id: "AUD1007", timestamp: "2026-08-05T20:04:15", userId: "U006", userName: "Anjali Mehta", role: "Management", module: "Reports", action: "Report Exported", affectedRecord: "RPT-SAL-2026-07", oldValue: null, newValue: { format: "PDF" }, ipAddress: "10.20.4.55", status: "Success", remarks: "" },
];

export const backups: Backup[] = [
  { id: "BKP-20260810", type: "Incremental", timestamp: "2026-08-10T02:00:00", size: "312 MB", location: "s3://epms-backups/2026-08-10-inc.tar.gz", createdBy: "Scheduler", status: "Completed", restoreStatus: "N/A", checksum: "a1f9c3...", remarks: "Automated nightly job." },
  { id: "BKP-20260808", type: "Full", timestamp: "2026-08-08T02:00:00", size: "1.8 GB", location: "s3://epms-backups/2026-08-08-full.tar.gz", createdBy: "Rohan Verma", status: "Completed", restoreStatus: "N/A", checksum: "88bd21...", remarks: "Weekly full backup." },
  { id: "BKP-20260803", type: "Differential", timestamp: "2026-08-03T02:00:00", size: "540 MB", location: "s3://epms-backups/2026-08-03-diff.tar.gz", createdBy: "Scheduler", status: "Completed", restoreStatus: "Restored", checksum: "5e02af...", remarks: "Restored to staging for QA on Aug 9." },
  { id: "BKP-20260801", type: "Full", timestamp: "2026-08-01T02:00:00", size: "1.7 GB", location: "s3://epms-backups/2026-08-01-full.tar.gz", createdBy: "Rohan Verma", status: "Failed", restoreStatus: "N/A", checksum: "\u2014", remarks: "Disk quota exceeded; retried successfully on Aug 3." },
];

export const systemMonitors: SystemMonitor[] = [
  { id: "MON01", component: "FastAPI", serviceStatus: "Online", cpuUsage: 34, memoryUsage: 48, databaseStatus: "Connected", responseTimeMs: 112, healthStatus: "Healthy", timestamp: "2026-08-11T10:00:00", alertStatus: "None" },
  { id: "MON02", component: "Uvicorn", serviceStatus: "Online", cpuUsage: 22, memoryUsage: 31, databaseStatus: "Connected", responseTimeMs: 45, healthStatus: "Healthy", timestamp: "2026-08-11T10:00:00", alertStatus: "None" },
  { id: "MON03", component: "MySQL", serviceStatus: "Online", cpuUsage: 51, memoryUsage: 67, databaseStatus: "Connected", responseTimeMs: 8, healthStatus: "Warning", timestamp: "2026-08-11T10:00:00", alertStatus: "Alert" },
  { id: "MON04", component: "Authentication", serviceStatus: "Online", cpuUsage: 12, memoryUsage: 19, databaseStatus: "Connected", responseTimeMs: 63, healthStatus: "Healthy", timestamp: "2026-08-11T10:00:00", alertStatus: "None" },
  { id: "MON05", component: "Payroll Service", serviceStatus: "Online", cpuUsage: 29, memoryUsage: 41, databaseStatus: "Connected", responseTimeMs: 158, healthStatus: "Healthy", timestamp: "2026-08-11T10:00:00", alertStatus: "None" },
  { id: "MON06", component: "Backup Service", serviceStatus: "Degraded", cpuUsage: 8, memoryUsage: 15, databaseStatus: "Connected", responseTimeMs: 210, healthStatus: "Warning", timestamp: "2026-08-11T10:00:00", alertStatus: "Alert" },
  { id: "MON07", component: "Scheduler", serviceStatus: "Online", cpuUsage: 5, memoryUsage: 12, databaseStatus: "Connected", responseTimeMs: 30, healthStatus: "Healthy", timestamp: "2026-08-11T10:00:00", alertStatus: "None" },
];

export const notifications: AppNotification[] = [
  { id: "N001", category: "Payroll", message: "August payroll validation completed with 1 critical issue.", timestamp: "2026-08-10T09:20:00", read: false },
  { id: "N002", category: "Leave", message: "Your leave request LV1002 was approved.", timestamp: "2026-08-09T16:45:00", read: false },
  { id: "N003", category: "System", message: "Nightly database backup completed successfully.", timestamp: "2026-08-10T02:05:00", read: true },
  { id: "N004", category: "Employee", message: "New employee Vikram Rane added to Operations.", timestamp: "2026-08-05T12:10:00", read: true },
  { id: "N005", category: "Security", message: "New login detected from a recognized device.", timestamp: "2026-08-06T08:55:00", read: true },
  { id: "N006", category: "Attendance", message: "3 employees marked late today.", timestamp: "2026-08-11T09:31:00", read: false },
];

export function employeeName(id: string | null): string {
  if (!id) return "\u2014";
  const e = employees.find((x) => x.id === id);
  return e ? `${e.firstName} ${e.lastName}` : id;
}
export function departmentName(id: string): string {
  return departments.find((d) => d.id === id)?.name ?? id;
}
export function designationName(id: string): string {
  return designations.find((d) => d.id === id)?.name ?? id;
}
