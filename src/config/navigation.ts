import type { Permission } from "@/types";
import {
  LayoutDashboard, Users, ShieldCheck, Building2, Briefcase, IdCard, CalendarCheck, CalendarClock,
  Wallet, PlayCircle, Receipt, FileCheck2, FileText, BarChart3, BellRing, DownloadCloud,
  ScrollText, DatabaseBackup, ActivitySquare,
} from "lucide-react";
import type { ComponentType } from "react";

export interface NavItem {
  label: string;
  path: string;
  icon: ComponentType<{ className?: string }>;
  permission?: Permission;
}

export interface NavGroup {
  label: string;
  items: NavItem[];
}

export const NAV_GROUPS: NavGroup[] = [
  {
    label: "Overview",
    items: [{ label: "Dashboard", path: "/", icon: LayoutDashboard }],
  },
  {
    label: "Identity & Access",
    items: [
      { label: "Users", path: "/users", icon: Users, permission: "users.manage" },
      { label: "Roles & Permissions", path: "/roles", icon: ShieldCheck, permission: "roles.manage" },
    ],
  },
  {
    label: "Organization",
    items: [
      { label: "Departments", path: "/organization/departments", icon: Building2, permission: "org.manage" },
      { label: "Designations", path: "/organization/designations", icon: Briefcase, permission: "org.manage" },
    ],
  },
  {
    label: "Employees",
    items: [
      { label: "Directory", path: "/employees", icon: IdCard, permission: "employee.view.all" },
      { label: "My Profile", path: "/my-profile", icon: IdCard },
    ],
  },
  {
    label: "Workforce",
    items: [
      { label: "Attendance", path: "/attendance", icon: CalendarCheck },
      { label: "Leave", path: "/leave", icon: CalendarClock },
    ],
  },
  {
    label: "Payroll",
    items: [
      { label: "Salary Structures", path: "/payroll/salary-structures", icon: Wallet, permission: "salary.view.all" },
      { label: "Payroll Processing", path: "/payroll/processing", icon: PlayCircle, permission: "payroll.view" },
      { label: "Deductions & Tax", path: "/payroll/deductions", icon: Receipt, permission: "payroll.view" },
      { label: "Payroll Validation", path: "/payroll/validation", icon: FileCheck2, permission: "payroll.validate" },
      { label: "Payslips", path: "/payroll/payslips", icon: FileText },
    ],
  },
  {
    label: "Reports & Analytics",
    items: [
      { label: "Salary Reports", path: "/reports/salary", icon: BarChart3, permission: "reports.view" },
      { label: "Leave Alerts", path: "/reports/leave-alerts", icon: BellRing, permission: "reports.view" },
      { label: "Exports", path: "/reports/exports", icon: DownloadCloud, permission: "reports.export" },
    ],
  },
  {
    label: "Governance",
    items: [{ label: "Audit Logs", path: "/audit", icon: ScrollText, permission: "audit.view" }],
  },
  {
    label: "Infrastructure",
    items: [
      { label: "Backup & Restore", path: "/infrastructure/backup", icon: DatabaseBackup, permission: "backup.create" },
      { label: "System Monitoring", path: "/infrastructure/monitoring", icon: ActivitySquare, permission: "monitoring.view" },
    ],
  },
];
