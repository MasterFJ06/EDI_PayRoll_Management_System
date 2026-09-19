import { Navigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { EmptyState } from "@/components/common/EmptyState";

export default function MyProfile() {
  const { user } = useAuth();
  if (!user?.employeeId) {
    return <EmptyState title="No employee record linked" description="This account is not linked to an employee profile." />;
  }
  return <Navigate to={`/employees/${user.employeeId}`} replace />;
}
