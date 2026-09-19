import { forwardRef, type InputHTMLAttributes } from "react";
import { Check } from "lucide-react";
import { cn } from "@/utils/cn";

export const Checkbox = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <span className="relative inline-flex h-4 w-4 shrink-0">
      <input type="checkbox" ref={ref} className="peer absolute inset-0 h-4 w-4 cursor-pointer opacity-0" {...props} />
      <span className={cn(
        "flex h-4 w-4 items-center justify-center rounded border border-border bg-white transition-colors",
        "peer-checked:bg-primary peer-checked:border-primary peer-focus-visible:ring-2 peer-focus-visible:ring-secondary peer-focus-visible:ring-offset-1",
        className
      )}>
        <Check className="h-3 w-3 text-white opacity-0 peer-checked:opacity-100" />
      </span>
    </span>
  )
);
Checkbox.displayName = "Checkbox";
