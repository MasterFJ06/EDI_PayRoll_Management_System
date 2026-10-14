import { useState, type FormEvent } from "react";
import { AlertCircle, Eye, EyeOff, LockKeyhole, UserRound } from "lucide-react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthProvider";

interface RedirectState { from?: { pathname?: string }; logoutWarning?: boolean }

export function LoginPage() {
  const { isAuthenticated, isSigningIn, signIn } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const redirectTo = (location.state as RedirectState | null)?.from?.pathname;
  const logoutWarning = (location.state as RedirectState | null)?.logoutWarning;

  if (isAuthenticated) return <Navigate to="/dashboard" replace />;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      await signIn(username.trim(), password);
      navigate(redirectTo || "/dashboard", { replace: true });
    } catch (caught) {
      setError(caught instanceof ApiError
        ? "Sign-in failed. Check your username and password, then try again."
        : "The sign-in service is unavailable. Please try again shortly.");
    }
  }

  return <main className="relative grid min-h-screen overflow-hidden bg-[#f6f8fb] lg:grid-cols-[1fr_0.9fr]">
    <div className="pointer-events-none absolute -left-32 -top-40 size-[520px] rounded-full border border-blue-100/70" />
    <div className="pointer-events-none absolute -left-16 -top-24 size-[380px] rounded-full border border-blue-100/70" />
    <section className="relative hidden flex-col justify-between px-12 py-10 lg:flex xl:px-20">
      <div className="flex items-center gap-3"><div className="grid size-11 place-items-center rounded-xl bg-blue-700 text-white shadow-lg shadow-blue-900/15"><span className="text-base font-bold">E</span></div><div><p className="text-sm font-semibold tracking-tight text-slate-900">EPMS</p><p className="text-[11px] text-slate-500">Employee Payroll Management System</p></div></div>
      <div className="relative max-w-lg pb-12">
        <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-blue-100 bg-white/80 px-3 py-1.5 text-[11px] font-semibold text-blue-700 shadow-sm"><span className="size-1.5 rounded-full bg-emerald-500" />Your people operations workspace</div>
        <h1 className="text-[42px] font-semibold leading-[1.12] tracking-[-0.04em] text-slate-900 xl:text-[50px]">Clear workflows.<br /><span className="text-blue-700">Confident operations.</span></h1>
        <p className="mt-5 max-w-md text-sm leading-7 text-slate-500">Access employee and payroll workflows through one secure, role-aware workspace.</p>
        <div className="mt-10 grid max-w-md grid-cols-2 gap-3">
          <div className="rounded-xl border border-slate-200 bg-white/80 p-4 shadow-sm"><div className="mb-4 grid size-9 place-items-center rounded-lg bg-blue-50 text-blue-700"><UserRound size={17} /></div><p className="text-xs font-semibold text-slate-800">Employee workflows</p><p className="mt-1 text-[11px] leading-5 text-slate-500">Access follows your assigned permissions.</p></div>
          <div className="rounded-xl border border-slate-200 bg-white/80 p-4 shadow-sm"><div className="mb-4 grid size-9 place-items-center rounded-lg bg-indigo-50 text-indigo-700"><LockKeyhole size={17} /></div><p className="text-xs font-semibold text-slate-800">Protected by EPMS</p><p className="mt-1 text-[11px] leading-5 text-slate-500">Access checks run on the backend.</p></div>
        </div>
      </div>
      <p className="text-[11px] text-slate-400">© {new Date().getFullYear()} EPMS · Internal system</p>
    </section>

    <section className="relative flex items-center justify-center px-4 py-10 sm:px-8 lg:border-l lg:border-slate-200/80 lg:bg-white/55">
      <div className="w-full max-w-[420px]">
        <div className="mb-8 flex items-center gap-3 lg:hidden"><div className="grid size-10 place-items-center rounded-xl bg-blue-700 text-white"><span className="text-sm font-bold">E</span></div><div><p className="text-sm font-semibold text-slate-900">EPMS</p><p className="text-[11px] text-slate-500">People workspace</p></div></div>
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xl shadow-slate-900/[0.04] sm:p-9">
          <div className="mb-7"><p className="text-xs font-semibold uppercase tracking-[0.12em] text-blue-700">Welcome back</p><h2 className="mt-2 text-2xl font-semibold tracking-tight text-slate-900">Sign in to EPMS</h2><p className="mt-2 text-sm leading-6 text-slate-500">Use your EPMS username and password to continue.</p></div>
          <form onSubmit={handleSubmit} className="space-y-5">
            {logoutWarning && <div role="status" className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2.5 text-xs leading-5 text-amber-900">You are signed out on this device, but the server did not confirm refresh-token revocation. Any remaining token expires according to the server refresh lifetime.</div>}
            <div><label htmlFor="username" className="mb-2 block text-xs font-semibold text-slate-700">Username</label><div className="relative"><UserRound className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" size={17} /><input id="username" name="username" autoComplete="username" required minLength={3} maxLength={50} value={username} onChange={(event) => setUsername(event.target.value)} className="h-11 w-full rounded-lg border border-slate-200 bg-white pl-10 pr-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 hover:border-slate-300 focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10" placeholder="Enter your username" /></div></div>
            <div><label htmlFor="password" className="mb-2 block text-xs font-semibold text-slate-700">Password</label><div className="relative"><LockKeyhole className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" size={17} /><input id="password" name="password" type={showPassword ? "text" : "password"} autoComplete="current-password" required minLength={8} maxLength={128} value={password} onChange={(event) => setPassword(event.target.value)} className="h-11 w-full rounded-lg border border-slate-200 bg-white pl-10 pr-11 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 hover:border-slate-300 focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10" placeholder="Enter your password" /><button type="button" onClick={() => setShowPassword((visible) => !visible)} className="absolute right-2 top-1/2 grid size-8 -translate-y-1/2 place-items-center rounded-md text-slate-400 transition hover:bg-slate-100 hover:text-slate-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600" aria-label={showPassword ? "Hide password" : "Show password"} aria-pressed={showPassword}>{showPassword ? <EyeOff size={16} /> : <Eye size={16} />}</button></div></div>
            {error && <div role="alert" className="flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2.5 text-xs leading-5 text-rose-700"><AlertCircle className="mt-0.5 shrink-0" size={15} /><span>{error}</span></div>}
            <button type="submit" disabled={isSigningIn || !username.trim() || password.length < 8} className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-blue-700 px-4 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-800 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-blue-600/20 disabled:cursor-not-allowed disabled:bg-blue-300">{isSigningIn ? "Signing in…" : "Sign in"}{!isSigningIn && <span aria-hidden="true">→</span>}</button>
          </form>
          <p className="mt-6 text-center text-[11px] leading-5 text-slate-400">Sign-in access is managed by your organization. Contact your administrator if you need an account.</p>
        </div>
        <p className="mt-5 text-center text-[10px] text-slate-400">Your session is held in memory and ends when this tab is reloaded.</p>
      </div>
    </section>
  </main>;
}
