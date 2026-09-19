import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import type { Permission } from "@/types";
import { LoadingState } from "@/components/common/LoadingState";

export function ProtectedRoute({ children, permission }: { children: ReactNode; permission?: Permission }) {
  const { isAuthenticated, isLoading, can } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <LoadingState label="Checking your session..." />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  if (permission && !can(permission)) {
    return <Navigate to="/forbidden" replace />;
  }

  return <>{children}</>;
}
