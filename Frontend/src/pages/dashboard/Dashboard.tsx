import { useAuth } from "@/context/AuthContext";
import EmployeeDashboard from "./EmployeeDashboard";
import ManagerDashboard from "./ManagerDashboard";
import HRDashboard from "./HRDashboard";
import PayrollDashboard from "./PayrollDashboard";
import AdminDashboard from "./AdminDashboard";
import ManagementDashboard from "./ManagementDashboard";

export default function Dashboard() {
  const { user } = useAuth();
  switch (user?.role) {
    case "Employee": return <EmployeeDashboard />;
    case "Manager": return <ManagerDashboard />;
    case "HR": return <HRDashboard />;
    case "Payroll Administrator": return <PayrollDashboard />;
    case "System Administrator": return <AdminDashboard />;
    case "Management": return <ManagementDashboard />;
    default: return null;
  }
}
