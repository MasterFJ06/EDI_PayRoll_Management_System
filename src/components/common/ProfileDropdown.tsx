import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronDown, LogOut, User, Settings, ShieldCheck } from "lucide-react";
import { useClickOutside } from "@/hooks/useClickOutside";
import { useAuth } from "@/context/AuthContext";
import { EmployeeAvatar } from "./EmployeeAvatar";
import { ALL_ROLES } from "@/config/permissions";
import type { Role } from "@/types";

export function ProfileDropdown() {
  const { user, logout, switchDemoRole } = useAuth();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  useClickOutside(ref, () => setOpen(false), open);

  if (!user) return null;

  async function handleLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 rounded-lg px-1.5 py-1 hover:bg-slate-100"
      >
        <EmployeeAvatar firstName={user.firstName} lastName={user.lastName} size="sm" />
        <div className="hidden text-left sm:block">
          <p className="text-xs font-semibold leading-tight text-text">{user.firstName} {user.lastName}</p>
          <p className="text-[11px] leading-tight text-text-muted">{user.role}</p>
        </div>
        <ChevronDown className="h-3.5 w-3.5 text-text-muted" />
      </button>
      {open && (
        <div className="absolute right-0 z-30 mt-2 w-56 rounded-xl border border-border bg-white shadow-xl">
          <div className="border-b border-border px-4 py-3">
            <p className="text-sm font-semibold text-text">{user.firstName} {user.lastName}</p>
            <p className="truncate text-xs text-text-muted">{user.email}</p>
          </div>
          <div className="p-1.5">
            <button onClick={() => { navigate("/my-profile"); setOpen(false); }} className="flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-left text-sm text-text hover:bg-slate-50">
              <User className="h-4 w-4 text-text-muted" /> My Profile
            </button>
            <button onClick={() => setOpen(false)} className="flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-left text-sm text-text hover:bg-slate-50">
              <Settings className="h-4 w-4 text-text-muted" /> Account Settings
            </button>
            <div className="my-1 border-t border-border" />
            <div className="px-2.5 py-2">
              <div className="mb-1.5 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wide text-text-muted">
                <ShieldCheck className="h-3.5 w-3.5" /> Demo role
              </div>
              <select
                value={user.role}
                onChange={(e) => switchDemoRole(e.target.value as Role)}
                className="w-full rounded-md border border-border bg-white px-2 py-1.5 text-xs text-text outline-none focus:border-secondary"
              >
                {ALL_ROLES.map((role) => <option key={role} value={role}>{role}</option>)}
              </select>
            </div>
            <button
              onClick={handleLogout}
              className="flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-left text-sm text-danger hover:bg-danger-50"
            >
              <LogOut className="h-4 w-4" /> Sign Out
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
