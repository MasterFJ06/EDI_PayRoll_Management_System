import { Routes, Route, Navigate } from "react-router-dom";
import { AppLayout } from "@/components/layout/AppLayout";
import { ProtectedRoute } from "./ProtectedRoute";
import Login from "@/pages/auth/Login";
import Register from "@/pages/auth/Register";
import Forbidden from "@/pages/auth/Forbidden";
import NotFound from "@/pages/NotFound";
import Dashboard from "@/pages/dashboard/Dashboard";
import UsersList from "@/pages/users/UsersList";
import RolesPermissions from "@/pages/users/RolesPermissions";
import Departments from "@/pages/organization/Departments";
import Designations from "@/pages/organization/Designations";
import EmployeeDirectory from "@/pages/employees/EmployeeDirectory";
import EmployeeProfile from "@/pages/employees/EmployeeProfile";
import MyProfile from "@/pages/employees/MyProfile";
import Attendance from "@/pages/attendance/Attendance";
import LeaveManagement from "@/pages/leave/LeaveManagement";
import SalaryStructures from "@/pages/payroll/SalaryStructures";
import PayrollProcessing from "@/pages/payroll/PayrollProcessing";
import Deductions from "@/pages/payroll/Deductions";
import PayrollValidation from "@/pages/payroll/PayrollValidation";
import Payslips from "@/pages/payroll/Payslips";
import SalaryReports from "@/pages/reports/SalaryReports";
import LeaveAlerts from "@/pages/reports/LeaveAlerts";
import Exports from "@/pages/reports/Exports";
import AuditLogs from "@/pages/audit/AuditLogs";
import BackupRestore from "@/pages/infrastructure/Backup";
import Monitoring from "@/pages/infrastructure/Monitoring";
import { useAuth } from "@/context/AuthContext";

export function AppRoutes() {
  const { isAuthenticated } = useAuth();

  return (
    <Routes>
      <Route path="/login" element={isAuthenticated ? <Navigate to="/" replace /> : <Login />} />
      <Route path="/register" element={isAuthenticated ? <Navigate to="/" replace /> : <Register />} />
      <Route path="/forbidden" element={<Forbidden />} />

      <Route element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
        <Route path="/" element={<Dashboard />} />

        <Route path="/users" element={<ProtectedRoute permission="users.manage"><UsersList /></ProtectedRoute>} />
        <Route path="/roles" element={<ProtectedRoute permission="roles.manage"><RolesPermissions /></ProtectedRoute>} />

        <Route path="/organization/departments" element={<ProtectedRoute permission="org.manage"><Departments /></ProtectedRoute>} />
        <Route path="/organization/designations" element={<ProtectedRoute permission="org.manage"><Designations /></ProtectedRoute>} />

        <Route path="/employees" element={<ProtectedRoute permission="employee.view.all"><EmployeeDirectory /></ProtectedRoute>} />
        <Route path="/employees/:id" element={<ProtectedRoute permission="employee.view.all"><EmployeeProfile /></ProtectedRoute>} />
        <Route path="/my-profile" element={<MyProfile />} />

        <Route path="/attendance" element={<Attendance />} />
        <Route path="/leave" element={<LeaveManagement />} />

        <Route path="/payroll/salary-structures" element={<ProtectedRoute permission="salary.view.all"><SalaryStructures /></ProtectedRoute>} />
        <Route path="/payroll/processing" element={<ProtectedRoute permission="payroll.view"><PayrollProcessing /></ProtectedRoute>} />
        <Route path="/payroll/deductions" element={<ProtectedRoute permission="payroll.view"><Deductions /></ProtectedRoute>} />
        <Route path="/payroll/validation" element={<ProtectedRoute permission="payroll.validate"><PayrollValidation /></ProtectedRoute>} />
        <Route path="/payroll/payslips" element={<Payslips />} />

        <Route path="/reports/salary" element={<ProtectedRoute permission="reports.view"><SalaryReports /></ProtectedRoute>} />
        <Route path="/reports/leave-alerts" element={<ProtectedRoute permission="reports.view"><LeaveAlerts /></ProtectedRoute>} />
        <Route path="/reports/exports" element={<ProtectedRoute permission="reports.export"><Exports /></ProtectedRoute>} />

        <Route path="/audit" element={<ProtectedRoute permission="audit.view"><AuditLogs /></ProtectedRoute>} />

        <Route path="/infrastructure/backup" element={<ProtectedRoute permission="backup.create"><BackupRestore /></ProtectedRoute>} />
        <Route path="/infrastructure/monitoring" element={<ProtectedRoute permission="monitoring.view"><Monitoring /></ProtectedRoute>} />
      </Route>

      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
