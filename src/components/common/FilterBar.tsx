import type { ReactNode } from "react";

export function FilterBar({ children }: { children: ReactNode }) {
  return <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">{children}</div>;
}
