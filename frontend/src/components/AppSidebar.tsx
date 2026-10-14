import { useState } from "react";
import { CalendarDays, CircleDollarSign, FileText, LayoutDashboard, Menu, UsersRound, WalletCards, X } from "lucide-react";
import { NavLink } from "react-router-dom";

const navItems = [
  { label: "Dashboard", to: "/dashboard", icon: LayoutDashboard },
  { label: "Employees", to: "/employees", icon: UsersRound },
  { label: "Attendance", to: "/attendance", icon: CalendarDays },
  { label: "Leave", to: "/leave", icon: CalendarDays },
  { label: "Compensation", to: "/compensation", icon: CircleDollarSign },
  { label: "Payroll", to: "/payroll", icon: WalletCards },
  { label: "Reports", to: "/reports", icon: FileText },
];

function Brand() {
  return <div className="flex items-center gap-3 px-5 py-5"><div className="grid size-10 place-items-center rounded-xl bg-blue-700 text-white shadow-sm shadow-blue-900/15"><span className="text-sm font-bold tracking-wide">E</span></div><div><p className="text-[15px] font-semibold tracking-tight text-slate-900">EPMS</p><p className="text-[11px] font-medium text-slate-400">People workspace</p></div></div>;
}

export function AppSidebar() {
  const [mobileOpen, setMobileOpen] = useState(false);
  return <>
    <button type="button" onClick={() => setMobileOpen(true)} className="fixed left-4 top-4 z-30 grid size-10 place-items-center rounded-lg border border-slate-200 bg-white text-slate-700 shadow-sm md:hidden" aria-label="Open navigation"><Menu size={18} /></button>
    {mobileOpen && <button className="fixed inset-0 z-40 bg-slate-950/30 md:hidden" aria-label="Close navigation overlay" onClick={() => setMobileOpen(false)} />}
    <aside className={`fixed inset-y-0 left-0 z-50 flex w-[258px] flex-col border-r border-slate-200 bg-white transition-transform duration-200 md:translate-x-0 ${mobileOpen ? "translate-x-0" : "-translate-x-full"}`} aria-label="Main navigation">
      <div className="flex items-center justify-between"><Brand /><button type="button" onClick={() => setMobileOpen(false)} className="mr-4 grid size-9 place-items-center rounded-lg text-slate-500 hover:bg-slate-100 md:hidden" aria-label="Close navigation"><X size={18} /></button></div>
      <div className="px-4 pt-5"><p className="px-3 pb-2 text-[10px] font-bold uppercase tracking-[0.14em] text-slate-400">Workspace</p>
        <nav className="space-y-1">{navItems.map(({ label, to, icon: Icon }) => to ? <NavLink key={label} to={to} onClick={() => setMobileOpen(false)} className={({ isActive }) => `group flex items-center gap-3 rounded-lg px-3 py-2.5 text-[13px] font-medium transition ${isActive ? "bg-blue-50 text-blue-700" : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"}`}><Icon size={17} strokeWidth={1.8} /><span>{label}</span></NavLink> : <div key={label} className="flex cursor-not-allowed items-center gap-3 rounded-lg px-3 py-2.5 text-[13px] font-medium text-slate-400" aria-disabled="true" title="This screen is not included in the current frontend slice."><Icon size={17} strokeWidth={1.8} /><span className="flex-1">{label}</span><span className="rounded bg-slate-100 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-slate-400">Soon</span></div>)}</nav>
      </div>
      <div className="mt-auto p-4"><div className="rounded-xl border border-slate-200 bg-slate-50 p-4"><p className="text-xs font-semibold text-slate-800">Need a hand?</p><p className="mt-1 text-[11px] leading-5 text-slate-500">Contact your EPMS administrator for access or account support.</p></div><p className="px-1 pt-4 text-[10px] text-slate-400">EPMS · Internal workspace</p></div>
    </aside>
  </>;
}
