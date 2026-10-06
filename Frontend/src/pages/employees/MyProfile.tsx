import type { ReactNode } from "react";
import { Mail, Phone, ShieldCheck, UserRound, BriefcaseBusiness, BadgeCheck } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { EmptyState } from "@/components/common/EmptyState";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { EmployeeAvatar } from "@/components/common/EmployeeAvatar";

export default function MyProfile() {
  const { user } = useAuth();

  if (!user) {
    return (
      <EmptyState
        title="Profile unavailable"
        description="You are not currently signed in."
      />
    );
  }

  const fullName = `${user.firstName} ${user.lastName}`.trim() || user.username;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text">My Profile</h1>
        <p className="mt-1 text-sm text-text-muted">
          View your account and employee information.
        </p>
      </div>

      <Card>
        <CardContent>
          <div className="flex flex-col gap-5 sm:flex-row sm:items-center">
            <EmployeeAvatar firstName={user.firstName} lastName={user.lastName} size="lg" />
            <div className="min-w-0">
              <h2 className="text-xl font-semibold text-text">{fullName}</h2>
              <p className="mt-1 text-sm font-medium text-secondary">{user.role}</p>
              <p className="mt-1 text-xs text-text-muted">Username: {user.username}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Personal Information</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-2">
              <InfoItem icon={<UserRound className="h-4 w-4" />} label="First Name" value={user.firstName || "—"} />
              <InfoItem icon={<UserRound className="h-4 w-4" />} label="Last Name" value={user.lastName || "—"} />
              <InfoItem icon={<Mail className="h-4 w-4" />} label="Email" value={user.email || "—"} />
              <InfoItem icon={<Phone className="h-4 w-4" />} label="Phone" value={user.phone || "—"} />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Account Information</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-2">
              <InfoItem icon={<BriefcaseBusiness className="h-4 w-4" />} label="Role" value={user.role} />
              <InfoItem icon={<BadgeCheck className="h-4 w-4" />} label="Status" value={user.status} />
              <InfoItem icon={<ShieldCheck className="h-4 w-4" />} label="Employee ID" value={user.employeeId || "Not linked"} />
              <InfoItem icon={<UserRound className="h-4 w-4" />} label="Username" value={user.username} />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function InfoItem({
  icon,
  label,
  value,
}: {
  icon: ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-slate-50 p-3">
      <div className="flex items-center gap-2 text-xs font-medium text-text-muted">
        {icon}
        <span>{label}</span>
      </div>
      <p className="mt-1 text-sm font-medium text-text break-words">{value}</p>
    </div>
  );
}
