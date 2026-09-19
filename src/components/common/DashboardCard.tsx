import type { ReactNode } from "react";
import { cn } from "@/utils/cn";
import { ArrowDownRight, ArrowUpRight } from "lucide-react";

interface DashboardCardProps {
  label: string;
  value: string;
  icon: ReactNode;
  trend?: { value: string; direction: "up" | "down"; positive?: boolean };
  tone?: "primary" | "success" | "warning" | "danger" | "info" | "neutral";
}

const TONE_BG: Record<string, string> = {
  primary: "bg-primary-50 text-primary",
  success: "bg-success-50 text-success",
  warning: "bg-warning-50 text-warning",
  danger: "bg-danger-50 text-danger",
  info: "bg-info-50 text-info",
  neutral: "bg-slate-100 text-slate-600",
};

export function DashboardCard({ label, value, icon, trend, tone = "primary" }: DashboardCardProps) {
  const positive = trend?.positive ?? trend?.direction === "up";
  return (
    <div className="rounded-xl border border-border bg-card p-4 shadow-[var(--shadow-card)]">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-text-muted">{label}</p>
          <p className="mt-1.5 text-2xl font-semibold tracking-tight text-text font-display">{value}</p>
        </div>
        <div className={cn("flex h-9 w-9 shrink-0 items-center justify-center rounded-lg", TONE_BG[tone])}>
          {icon}
        </div>
      </div>
      {trend && (
        <div className="mt-2.5 flex items-center gap-1 text-xs">
          <span className={cn("flex items-center gap-0.5 font-medium", positive ? "text-success" : "text-danger")}>
            {trend.direction === "up" ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
            {trend.value}
          </span>
          <span className="text-text-muted">vs last month</span>
        </div>
      )}
    </div>
  );
}
