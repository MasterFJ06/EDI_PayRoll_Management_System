import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth/AuthProvider";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { AppShell } from "./components/AppShell";
import { DashboardPage } from "./pages/DashboardPage";
import { CreateEmployeePage } from "./pages/CreateEmployeePage";
import { EmployeeDetailPage } from "./pages/EmployeeDetailPage";
import { EmployeeDirectoryPage } from "./pages/EmployeeDirectoryPage";
import { AttendancePage } from "./pages/AttendancePage";
import { CreateAttendancePage } from "./pages/CreateAttendancePage";
import { LeaveAllocationsPage } from "./pages/LeaveAllocationsPage";
import { LeaveBalancesPage } from "./pages/LeaveBalancesPage";
import { CreateLeaveRequestPage } from "./pages/CreateLeaveRequestPage";
import { CreateLeaveBalancePage } from "./pages/CreateLeaveBalancePage";
import { CompensationPage } from "./pages/CompensationPage";
import { PayrollPage } from "./pages/PayrollPage";
import { ReportsPage } from "./pages/ReportsPage";
import { LoginPage } from "./pages/LoginPage";
import { NotFoundPage } from "./pages/NotFoundPage";

export function App() {
  const { isAuthenticated } = useAuth();
  return (
    <Routes>
      <Route path="/" element={<Navigate to={isAuthenticated ? "/dashboard" : "/login"} replace />} />
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/employees" element={<EmployeeDirectoryPage />} />
          <Route path="/employees/new" element={<CreateEmployeePage />} />
          <Route path="/employees/:employeeCode" element={<EmployeeDetailPage />} />
          <Route path="/attendance" element={<AttendancePage />} />
          <Route path="/attendance/new" element={<CreateAttendancePage />} />
          <Route path="/leave" element={<Navigate to="/leave/requests" replace />} />
          <Route path="/leave/requests" element={<LeaveAllocationsPage />} />
          <Route path="/leave/requests/new" element={<CreateLeaveRequestPage />} />
          <Route path="/leave/balances" element={<LeaveBalancesPage />} />
          <Route path="/leave/balances/new" element={<CreateLeaveBalancePage />} />
          <Route path="/compensation" element={<CompensationPage />} />
          <Route path="/payroll" element={<PayrollPage />} />
          <Route path="/reports" element={<ReportsPage />} />
        </Route>
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
