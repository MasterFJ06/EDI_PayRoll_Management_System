import type { LabelHTMLAttributes } from "react";
import { cn } from "@/utils/cn";

export function Label({ className, children, ...props }: LabelHTMLAttributes<HTMLLabelElement> & { required?: boolean }) {
  return (
    <label className={cn("mb-1.5 block text-sm font-medium text-text", className)} {...props}>
      {children}
      {props.required && <span className="text-danger ml-0.5">*</span>}
    </label>
  );
}
