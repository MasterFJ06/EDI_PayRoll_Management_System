import { NavLink } from "react-router-dom";
import { X, ShieldHalf } from "lucide-react";
import { NAV_GROUPS } from "@/config/navigation";
import { useAuth } from "@/context/AuthContext";
import { cn } from "@/utils/cn";

interface SidebarProps {
  mobileOpen: boolean;
  onCloseMobile: () => void;
}

export function Sidebar({ mobileOpen, onCloseMobile }: SidebarProps) {
  const { user, can } = useAuth();

  const content = (
    <div className="flex h-full flex-col bg-primary-700">
      <div className="flex items-center gap-2.5 px-5 py-5">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-white/10 text-white">
          <ShieldHalf className="h-5 w-5" />
        </div>
        <div className="min-w-0">
          <p className="font-display text-base font-bold leading-tight text-white">EPMS</p>
          <p className="truncate text-[11px] leading-tight text-blue-200/80">Employee Payroll Mgmt System</p>
        </div>
        <button
          onClick={onCloseMobile}
          className="ml-auto rounded-md p-1 text-blue-200 hover:bg-white/10 lg:hidden"
          aria-label="Close navigation"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 pb-4 scrollbar-thin">
        {NAV_GROUPS.map((group) => {
          const visibleItems = group.items.filter((item) => !item.permission || can(item.permission));
          if (visibleItems.length === 0) return null;
          return (
            <div key={group.label} className="mb-4">
              <p className="mb-1.5 px-2.5 text-[10px] font-semibold uppercase tracking-wider text-blue-300/70">
                {group.label}
              </p>
              <div className="space-y-0.5">
                {visibleItems.map((item) => (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    end={item.path === "/"}
                    onClick={onCloseMobile}
                    className={({ isActive }) =>
                      cn(
                        "flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm font-medium transition-colors",
                        isActive
                          ? "bg-white text-primary shadow-sm"
                          : "text-blue-100 hover:bg-white/10 hover:text-white"
                      )
                    }
                  >
                    <item.icon className="h-4 w-4 shrink-0" />
                    <span className="truncate">{item.label}</span>
                  </NavLink>
                ))}
              </div>
            </div>
          );
        })}
      </nav>

      <div className="mx-3 mb-4 rounded-lg bg-white/5 p-3">
        <p className="text-[11px] font-medium text-blue-200/80">Signed in as</p>
        <p className="truncate text-sm font-semibold text-white">{user?.firstName} {user?.lastName}</p>
        <p className="truncate text-[11px] text-blue-300/70">{user?.role}</p>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop / tablet */}
      <aside className="hidden w-64 shrink-0 lg:block">
        <div className="fixed inset-y-0 left-0 w-64">{content}</div>
      </aside>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-slate-900/50" onClick={onCloseMobile} />
          <aside className="absolute inset-y-0 left-0 w-64">{content}</aside>
        </div>
      )}
    </>
  );
}
