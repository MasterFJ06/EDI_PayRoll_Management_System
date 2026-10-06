import { initials } from "@/utils/format";
import { cn } from "@/utils/cn";

const COLORS = ["bg-blue-500", "bg-indigo-500", "bg-emerald-500", "bg-amber-500", "bg-sky-600", "bg-rose-500", "bg-violet-500", "bg-teal-500"];

function colorFor(seed: string) {
  let hash = 0;
  for (let i = 0; i < seed.length; i++) hash = seed.charCodeAt(i) + ((hash << 5) - hash);
  return COLORS[Math.abs(hash) % COLORS.length];
}

interface EmployeeAvatarProps {
  firstName: string;
  lastName: string;
  size?: "sm" | "md" | "lg";
  className?: string;
}

const SIZE = { sm: "h-7 w-7 text-[11px]", md: "h-9 w-9 text-xs", lg: "h-14 w-14 text-base" };

export function EmployeeAvatar({ firstName, lastName, size = "md", className }: EmployeeAvatarProps) {
  return (
    <div
      className={cn(
        "flex shrink-0 items-center justify-center rounded-full font-semibold text-white",
        SIZE[size], colorFor(firstName + lastName), className
      )}
    >
      {initials(firstName, lastName)}
    </div>
  );
}
