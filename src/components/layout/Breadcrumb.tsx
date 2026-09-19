import { Link, useLocation } from "react-router-dom";
import { ChevronRight, Home } from "lucide-react";
import { NAV_GROUPS } from "@/config/navigation";

const LABEL_OVERRIDES: Record<string, string> = {
  "my-profile": "My Profile",
  roles: "Roles & Permissions",
};

function labelFor(path: string): string {
  const flat = NAV_GROUPS.flatMap((g) => g.items);
  const match = flat.find((i) => i.path === path);
  if (match) return match.label;
  const segment = path.split("/").filter(Boolean).pop() ?? "";
  return LABEL_OVERRIDES[segment] ?? segment.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function Breadcrumb() {
  const location = useLocation();
  const segments = location.pathname.split("/").filter(Boolean);

  if (segments.length === 0) {
    return (
      <div className="flex items-center gap-1.5 text-xs text-text-muted">
        <Home className="h-3.5 w-3.5" /> <span className="text-text font-medium">Dashboard</span>
      </div>
    );
  }

  let cumulative = "";
  return (
    <div className="flex items-center gap-1.5 text-xs text-text-muted">
      <Link to="/" className="flex items-center hover:text-text"><Home className="h-3.5 w-3.5" /></Link>
      {segments.map((seg, i) => {
        cumulative += `/${seg}`;
        const isLast = i === segments.length - 1;
        return (
          <span key={cumulative} className="flex items-center gap-1.5">
            <ChevronRight className="h-3 w-3" />
            {isLast ? (
              <span className="font-medium text-text">{labelFor(cumulative)}</span>
            ) : (
              <Link to={cumulative} className="hover:text-text">{labelFor(cumulative)}</Link>
            )}
          </span>
        );
      })}
    </div>
  );
}
