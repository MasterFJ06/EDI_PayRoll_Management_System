import { Badge } from "@/components/ui/Badge";

const STATUS_MAP: Record<string, { variant: "success" | "warning" | "danger" | "info" | "neutral" | "primary" }> = {
  Active: { variant: "success" }, Present: { variant: "success" }, Approved: { variant: "success" },
  Completed: { variant: "success" }, Paid: { variant: "success" }, Healthy: { variant: "success" },
  Online: { variant: "success" }, Connected: { variant: "success" }, Resolved: { variant: "success" },
  Success: { variant: "success" }, Generated: { variant: "success" }, Sent: { variant: "success" },

  Pending: { variant: "warning" }, "Half-Day": { variant: "warning" }, Late: { variant: "warning" },
  Warning: { variant: "warning" }, Draft: { variant: "warning" }, Processing: { variant: "warning" },
  Degraded: { variant: "warning" }, "On Leave": { variant: "warning" }, Open: { variant: "warning" },

  Inactive: { variant: "neutral" }, Cancelled: { variant: "neutral" }, "N/A": { variant: "neutral" },

  Absent: { variant: "danger" }, Rejected: { variant: "danger" }, Failed: { variant: "danger" },
  Critical: { variant: "danger" }, Terminated: { variant: "danger" }, Suspended: { variant: "danger" },
  Offline: { variant: "danger" }, Disconnected: { variant: "danger" }, Error: { variant: "danger" },
  Alert: { variant: "danger" },

  Validated: { variant: "info" }, Processed: { variant: "info" }, Information: { variant: "info" },
  Restored: { variant: "info" }, "In Progress": { variant: "info" }, Downloaded: { variant: "info" },
};

export function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_MAP[status] ?? { variant: "neutral" as const };
  return <Badge variant={cfg.variant} dot>{status}</Badge>;
}
