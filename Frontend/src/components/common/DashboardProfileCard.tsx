import { Mail, Phone, UserRound } from "lucide-react";
import { Link } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { EmployeeAvatar } from "./EmployeeAvatar";
import { Card, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";

export function DashboardProfileCard() {
  const { user } = useAuth();
  if (!user) return null;

  return (
    <Card>
      <CardContent>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex min-w-0 items-center gap-3">
            <EmployeeAvatar firstName={user.firstName} lastName={user.lastName} size="lg" />
            <div className="min-w-0">
              <p className="text-base font-semibold text-text">{user.firstName} {user.lastName}</p>
              <p className="text-sm font-medium text-secondary">{user.role}</p>
              <div className="mt-1 flex flex-col gap-1 text-xs text-text-muted sm:flex-row sm:gap-3">
                <span className="inline-flex items-center gap-1"><Mail className="h-3.5 w-3.5" />{user.email}</span>
                <span className="inline-flex items-center gap-1"><Phone className="h-3.5 w-3.5" />{user.phone}</span>
              </div>
            </div>
          </div>
          <Link to="/my-profile" className="shrink-0">
            <Button variant="outline" size="sm"><UserRound className="mr-1.5 h-4 w-4" />View My Profile</Button>
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}
