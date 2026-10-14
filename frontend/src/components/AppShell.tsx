import { Outlet, useLocation } from "react-router-dom";
import { AppSidebar } from "./AppSidebar";
import { TopBar } from "./TopBar";

export function AppShell() {
  const pathname = useLocation().pathname;
  const title = pathname === "/dashboard"
    ? "Dashboard"
    : pathname === "/employees"
      ? "Employee directory"
      : pathname === "/employees/new"
        ? "Add employee"
        : pathname.startsWith("/employees/")
          ? "Employee details"
        : pathname.startsWith("/attendance")
          ? pathname === "/attendance/new" ? "Record attendance" : "Attendance"
          : pathname.startsWith("/leave/balances")
            ? pathname === "/leave/balances/new" ? "Create Leave balance" : "Leave balances"
            : pathname.startsWith("/leave")
              ? pathname === "/leave/requests/new" ? "Create Leave request" : "Leave requests"
          : pathname.startsWith("/compensation")
            ? "Compensation"
          : pathname.startsWith("/payroll")
            ? "Payroll processing"
          : pathname === "/reports"
            ? "Reports"
          : "Workspace";
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <AppSidebar />
      <div className="min-h-screen md:pl-[258px]">
        <TopBar title={title} />
        <main className="mx-auto w-full max-w-[1440px] px-4 pb-10 pt-7 sm:px-7 lg:px-10">
          <Outlet />
        </main>
        <footer className="mx-auto max-w-[1440px] px-4 pb-6 text-xs text-slate-400 sm:px-7 lg:px-10">
          EPMS workspace · Payroll and employee data access is enforced by the backend.
        </footer>
      </div>
    </div>
  );
}
