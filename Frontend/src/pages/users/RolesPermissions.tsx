import { useState, Fragment } from "react";
import { ShieldCheck, Check } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { Card, CardContent } from "@/components/ui/Card";
import { StatusBadge } from "@/components/common/StatusBadge";
import { ROLE_PERMISSIONS, ALL_ROLES, ALL_PERMISSIONS } from "@/config/permissions";

const ROLE_DESCRIPTIONS: Record<string, string> = {
  Employee: "Self-service access to personal attendance, leave and payroll information.",
  Manager: "Team visibility, attendance oversight and leave approvals for direct reports.",
  HR: "Full employee lifecycle, organization structure and leave administration.",
  "Payroll Administrator": "Salary structures, payroll processing, validation and payslip generation.",
  "System Administrator": "User accounts, roles, backups and system infrastructure monitoring.",
  Management: "Read-only visibility into workforce, payroll and organizational reporting.",
};

const MODULE_ACTIONS: { module: string; actions: string[] }[] = [
  { module: "Employee", actions: ["view.self", "view.all", "create", "update", "delete"] },
  { module: "Attendance", actions: ["view.self", "view.all", "create", "update"] },
  { module: "Leave", actions: ["apply", "view.self", "view.all", "approve", "reject"] },
  { module: "Salary", actions: ["view.self", "view.all", "create", "update"] },
  { module: "Payroll", actions: ["view", "process", "approve", "validate"] },
  { module: "Payslip", actions: ["view.self", "view.all", "generate"] },
  { module: "Reports", actions: ["view", "export"] },
];

export default function RolesPermissions() {
  const [activeRole, setActiveRole] = useState<string>(ALL_ROLES[0]);

  return (
    <div>
      <PageHeader
        title="Roles & Permissions"
        description="Frontend RBAC configuration. The FastAPI backend independently enforces every permission via JWT."
        icon={<ShieldCheck className="h-5 w-5" />}
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 mb-6">
        {ALL_ROLES.map((role) => (
          <Card key={role} className="overflow-hidden">
            <CardContent>
              <div className="flex items-center justify-between">
                <p className="font-semibold text-text">{role}</p>
                <StatusBadge status="Active" />
              </div>
              <p className="mt-1.5 text-xs text-text-muted">{ROLE_DESCRIPTIONS[role]}</p>
              <p className="mt-3 text-xs font-medium text-secondary">{ROLE_PERMISSIONS[role].length} permissions granted</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardContent>
          <p className="mb-1 text-sm font-semibold text-text">Permission Matrix</p>
          <p className="mb-4 text-xs text-text-muted">Grouped view of module-level actions across all six roles. Full permission keys are listed below.</p>

          <div className="overflow-x-auto scrollbar-thin">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="px-3 py-2.5 text-xs font-semibold uppercase tracking-wide text-text-muted">Module / Action</th>
                  {ALL_ROLES.map((r) => (
                    <th key={r} className="px-3 py-2.5 text-center text-xs font-semibold uppercase tracking-wide text-text-muted">
                      {r.split(" ").map((w) => w[0]).join("")}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {MODULE_ACTIONS.map((group) => (
                  <Fragment key={group.module}>
                    <tr className="bg-slate-50/70">
                      <td colSpan={ALL_ROLES.length + 1} className="px-3 py-1.5 text-xs font-semibold text-text">{group.module}</td>
                    </tr>
                    {group.actions.map((action) => {
                      const permKey = `${group.module.toLowerCase()}.${action}`;
                      return (
                        <tr key={permKey} className="border-b border-border last:border-0">
                          <td className="px-3 py-2 text-text-muted">{action}</td>
                          {ALL_ROLES.map((role) => {
                            const granted = ROLE_PERMISSIONS[role].includes(permKey as never);
                            return (
                              <td key={role} className="px-3 py-2 text-center">
                                {granted ? <Check className="mx-auto h-4 w-4 text-success" /> : <span className="text-slate-300">\u2014</span>}
                              </td>
                            );
                          })}
                        </tr>
                      );
                    })}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <Card className="mt-6">
        <CardContent>
          <div className="mb-3 flex flex-wrap gap-1.5">
            {ALL_ROLES.map((r) => (
              <button
                key={r}
                onClick={() => setActiveRole(r)}
                className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${activeRole === r ? "border-primary bg-primary-50 text-primary" : "border-border text-text-muted hover:text-text"}`}
              >
                {r}
              </button>
            ))}
          </div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-text-muted">Raw permission keys for {activeRole}</p>
          <div className="flex flex-wrap gap-1.5">
            {ROLE_PERMISSIONS[activeRole as keyof typeof ROLE_PERMISSIONS].map((p) => (
              <code key={p} className="rounded-md bg-slate-100 px-2 py-1 text-[11px] text-text">{p}</code>
            ))}
          </div>
          <p className="mt-4 text-xs text-text-muted">
            {ALL_PERMISSIONS.length} unique permissions defined across the system.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
