import { LogOut, UserRound } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthProvider";

export function TopBar({ title }: { title: string }) {
  const { signOut } = useAuth();
  const navigate = useNavigate();
  async function handleSignOut() {
    const revocationConfirmed = await signOut();
    navigate("/login", { replace: true, state: { logoutWarning: !revocationConfirmed } });
  }
  return (
    <header className="sticky top-0 z-20 flex h-[72px] items-center justify-between border-b border-slate-200/80 bg-white/95 px-4 backdrop-blur sm:px-7 lg:px-10">
      <div className="pl-12 md:pl-0">
        <p className="text-[11px] font-medium text-slate-400">EPMS / Workspace</p>
        <h1 className="mt-0.5 text-sm font-semibold tracking-tight text-slate-800">{title}</h1>
      </div>
      <div className="flex items-center gap-3">
        <div className="hidden items-center gap-2 border-r border-slate-200 pr-4 sm:flex">
          <div className="grid size-8 place-items-center rounded-full bg-blue-50 text-blue-700"><UserRound size={15} /></div>
          <div><p className="text-xs font-semibold text-slate-700">Signed in</p><p className="text-[10px] text-slate-400">Account session</p></div>
        </div>
        <button type="button" onClick={() => void handleSignOut()} className="inline-flex h-9 items-center gap-2 rounded-lg border border-slate-200 px-3 text-xs font-semibold text-slate-600 transition hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2">
          <LogOut size={15} /><span className="hidden sm:inline">Sign out</span><span className="sm:hidden">Logout</span>
        </button>
      </div>
    </header>
  );
}
