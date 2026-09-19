import { forwardRef, type InputHTMLAttributes } from "react";
import { cn } from "@/utils/cn";

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  error?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, error, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        "flex h-9 w-full rounded-lg border bg-white px-3 py-2 text-sm text-text placeholder:text-text-muted transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary focus-visible:border-secondary",
        "disabled:cursor-not-allowed disabled:opacity-50",
        error ? "border-danger" : "border-border",
        className
      )}
      {...props}
    />
  )
);
Input.displayName = "Input";
