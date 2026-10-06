import { useRef, useState } from "react";
import { Bell, CheckCheck } from "lucide-react";
import { useClickOutside } from "@/hooks/useClickOutside";
import { notifications as seedNotifications } from "@/data/mockData";
import { cn } from "@/utils/cn";

const CATEGORY_DOT: Record<string, string> = {
  Payroll: "bg-amber-500", Leave: "bg-sky-500", Attendance: "bg-emerald-500",
  Security: "bg-red-500", Employee: "bg-indigo-500", System: "bg-slate-500",
};

function timeAgo(ts: string) {
  const diffMs = Date.now() - new Date(ts).getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 60) return `${Math.max(mins, 1)}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export function NotificationDropdown() {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState(seedNotifications);
  const ref = useRef<HTMLDivElement>(null);
  useClickOutside(ref, () => setOpen(false), open);

  const unread = items.filter((n) => !n.read).length;

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        aria-label="Notifications"
        className="relative flex h-9 w-9 items-center justify-center rounded-lg text-text-muted hover:bg-slate-100 hover:text-text"
      >
        <Bell className="h-[18px] w-[18px]" />
        {unread > 0 && (
          <span className="absolute right-1.5 top-1.5 flex h-2 w-2 rounded-full bg-danger ring-2 ring-white" />
        )}
      </button>
      {open && (
        <div className="absolute right-0 z-30 mt-2 w-80 rounded-xl border border-border bg-white shadow-xl">
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <p className="text-sm font-semibold text-text">Notifications</p>
            <button
              onClick={() => setItems((prev) => prev.map((n) => ({ ...n, read: true })))}
              className="flex items-center gap-1 text-xs font-medium text-secondary hover:underline"
            >
              <CheckCheck className="h-3.5 w-3.5" /> Mark all read
            </button>
          </div>
          <div className="max-h-80 overflow-y-auto scrollbar-thin">
            {items.map((n) => (
              <button
                key={n.id}
                onClick={() => setItems((prev) => prev.map((x) => (x.id === n.id ? { ...x, read: true } : x)))}
                className={cn("flex w-full gap-2.5 border-b border-border px-4 py-3 text-left last:border-0 hover:bg-slate-50", !n.read && "bg-primary-50/40")}
              >
                <span className={cn("mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full", CATEGORY_DOT[n.category])} />
                <div className="min-w-0">
                  <p className={cn("text-xs leading-snug text-text", !n.read && "font-medium")}>{n.message}</p>
                  <p className="mt-0.5 text-[11px] text-text-muted">{n.category} \u00b7 {timeAgo(n.timestamp)}</p>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
