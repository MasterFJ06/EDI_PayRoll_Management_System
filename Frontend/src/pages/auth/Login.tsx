import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Eye, EyeOff, ShieldHalf, Loader2, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Checkbox } from "@/components/ui/Checkbox";
import { useAuth } from "@/context/AuthContext";
import { DEMO_ACCOUNTS } from "@/services/authService";
import { USE_MOCKS } from "@/services/api";

const schema = z.object({
  username: z.string().min(1, "Username or email is required"),
  password: z.string().min(1, "Password is required"),
  rememberMe: z.boolean(),
});
type FormValues = z.infer<typeof schema>;

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [showPassword, setShowPassword] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register, handleSubmit, formState: { errors, isSubmitting }, setValue,
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { username: "", password: "", rememberMe: true },
  });

  async function onSubmit(values: FormValues) {
    setServerError(null);
    try {
      await login(values);
      const from = (location.state as { from?: string })?.from ?? "/";
      navigate(from, { replace: true });
    } catch (err) {
      setServerError(err instanceof Error ? err.message : "Unable to sign in. Please try again.");
    }
  }

  return (
    <div className="flex min-h-screen bg-bg">
      {/* Brand panel */}
      <div className="relative hidden w-1/2 flex-col justify-between overflow-hidden bg-primary p-10 text-white lg:flex">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(255,255,255,0.08),transparent_45%),radial-gradient(circle_at_80%_80%,rgba(255,255,255,0.06),transparent_45%)]" />
        <div className="relative flex items-center gap-2.5">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-white/10">
            <ShieldHalf className="h-5 w-5" />
          </div>
          <div>
            <p className="font-display text-lg font-bold leading-tight">EPMS</p>
            <p className="text-xs text-blue-200">Employee Payroll Management System</p>
          </div>
        </div>
        <div className="relative max-w-md">
          <h1 className="font-display text-3xl font-bold leading-tight">
            One platform for people, attendance and payroll.
          </h1>
          <p className="mt-4 text-sm text-blue-100/90">
            Manage employees, attendance, leave and end-to-end payroll processing
            with role-based access, audit trails and enterprise-grade reporting.
          </p>
        </div>
        <p className="relative text-xs text-blue-200/70">© 2026 EPMS \u00b7 Built for modern HR & payroll teams.</p>
      </div>

      {/* Form panel */}
      <div className="flex w-full flex-col items-center justify-center px-6 py-12 lg:w-1/2">
        <div className="w-full max-w-sm">
          <div className="mb-8 flex items-center gap-2.5 lg:hidden">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-white">
              <ShieldHalf className="h-5 w-5" />
            </div>
            <div>
              <p className="font-display text-lg font-bold leading-tight text-text">EPMS</p>
              <p className="text-xs text-text-muted">Employee Payroll Management System</p>
            </div>
          </div>

          <h2 className="font-display text-2xl font-semibold text-text">Welcome back</h2>
          <p className="mt-1 text-sm text-text-muted">Sign in to access your payroll workspace.</p>

          {serverError && (
            <div className="mt-5 flex items-start gap-2 rounded-lg border border-red-200 bg-danger-50 px-3.5 py-2.5 text-sm text-danger">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{serverError}</span>
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="mt-6 space-y-4" noValidate>
            <div>
              <Label htmlFor="username" required>Email / Username</Label>
              <Input
                id="username"
                autoComplete="username"
                placeholder="e.g. priya.sharma"
                error={!!errors.username}
                {...register("username")}
              />
              {errors.username && <p className="mt-1 text-xs text-danger">{errors.username.message}</p>}
            </div>

            <div>
              <Label htmlFor="password" required>Password</Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  placeholder="Enter your password"
                  error={!!errors.password}
                  className="pr-10"
                  {...register("password")}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((s) => !s)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              {errors.password && <p className="mt-1 text-xs text-danger">{errors.password.message}</p>}
            </div>

            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 text-sm text-text-muted">
                <Checkbox defaultChecked onChange={(e) => setValue("rememberMe", e.target.checked)} />
                Remember me
              </label>
              <span className="text-xs text-text-muted">Password reset is handled by the backend/admin workflow.</span>
            </div>

            <Button type="submit" className="w-full" size="lg" loading={isSubmitting}>
              {isSubmitting ? "Signing in..." : "Sign In"}
            </Button>
          </form>

          <div className="mt-5 text-center text-sm text-text-muted">New here? <Link to="/register" className="font-semibold text-secondary hover:underline">Create an account</Link></div>

          {USE_MOCKS && <div className="mt-8 rounded-xl border border-border bg-white p-4">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-text-muted">Demo accounts (any password)</p>
            <div className="grid grid-cols-2 gap-1.5">
              {DEMO_ACCOUNTS.map((acc) => (
                <button
                  key={acc.username}
                  type="button"
                  onClick={() => { setValue("username", acc.username); }}
                  className="rounded-md border border-border px-2 py-1.5 text-left text-[11px] hover:border-secondary hover:bg-secondary-50"
                >
                  <p className="truncate font-medium text-text">{acc.username}</p>
                  <p className="truncate text-text-muted">{acc.role}</p>
                </button>
              ))}
            </div>
          </div>}
        </div>
      </div>
    </div>
  );
}

export function LoginRedirectingOverlay() {
  return (
    <div className="fixed inset-0 flex items-center justify-center bg-white/70">
      <Loader2 className="h-6 w-6 animate-spin text-primary" />
    </div>
  );
}
