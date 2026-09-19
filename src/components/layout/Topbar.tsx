import { Menu } from "lucide-react";
import { Breadcrumb } from "./Breadcrumb";
import { GlobalSearch } from "@/components/common/GlobalSearch";
import { NotificationDropdown } from "@/components/common/NotificationDropdown";
import { ProfileDropdown } from "@/components/common/ProfileDropdown";

export function Topbar({ onOpenMobile }: { onOpenMobile: () => void }) {
  return (
    <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-border bg-white/90 px-4 backdrop-blur sm:px-6">
      <button
        onClick={onOpenMobile}
        className="flex h-9 w-9 items-center justify-center rounded-lg text-text-muted hover:bg-slate-100 lg:hidden"
        aria-label="Open navigation"
      >
        <Menu className="h-5 w-5" />
      </button>
      <div className="hidden lg:block">
        <Breadcrumb />
      </div>
      <div className="flex flex-1 items-center justify-end gap-2 sm:gap-3">
        <GlobalSearch />
        <NotificationDropdown />
        <div className="h-6 w-px bg-border hidden sm:block" />
        <ProfileDropdown />
      </div>
    </header>
  );
}
