import type { HTMLAttributes } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/utils/cn";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium border",
  {
    variants: {
      variant: {
        neutral: "bg-slate-100 text-slate-600 border-slate-200",
        primary: "bg-primary-50 text-primary border-primary-100",
        success: "bg-success-50 text-success border-green-200",
        warning: "bg-warning-50 text-warning border-amber-200",
        danger: "bg-danger-50 text-danger border-red-200",
        info: "bg-info-50 text-info border-sky-200",
      },
    },
    defaultVariants: { variant: "neutral" },
  }
);

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {
  dot?: boolean;
}

export function Badge({ className, variant, dot, children, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant }), className)} {...props}>
      {dot && <span className={cn("h-1.5 w-1.5 rounded-full",
        variant === "success" && "bg-success",
        variant === "warning" && "bg-warning",
        variant === "danger" && "bg-danger",
        variant === "info" && "bg-info",
        (variant === "neutral" || !variant) && "bg-slate-400",
        variant === "primary" && "bg-primary",
      )} />}
      {children}
    </span>
  );
}
