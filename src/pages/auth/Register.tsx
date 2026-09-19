import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Link, useNavigate } from "react-router-dom";
import { ShieldHalf, UserPlus } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Select } from "@/components/ui/Select";

import { createUser, listUsers, setUserPassword } from "@/services/userService";
import { registerUser } from "@/services/authService";
import { USE_MOCKS } from "@/services/api";


const schema = z.object({
  firstName: z.string().min(1, "First name is required"),
  lastName: z.string().min(1, "Last name is required"),
  username: z.string().min(3, "Username must be at least 3 characters"),
  email: z.string().email("Enter a valid email address"),
  phone: z.string().min(10, "Enter a valid phone number"),
  employeeId: z.string().optional(),
  role: z.string().min(1),
  password: z.string().min(8, "Password must be at least 8 characters"),
  confirmPassword: z.string().min(1, "Confirm your password"),
}).refine((d) => d.password === d.confirmPassword, { path: ["confirmPassword"], message: "Passwords do not match" });

type FormValues = z.infer<typeof schema>;

export default function Register() {
  const navigate = useNavigate();
  const [serverError, setServerError] = useState<string | null>(null);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { role: "Employee" },
  });

  async function onSubmit(values: FormValues) {
    setServerError(null);
    if (USE_MOCKS) {
      const existing = await listUsers();
      if (existing.some((u) => u.username.toLowerCase() === values.username.toLowerCase())) {
        setServerError("That username is already registered.");
        return;
      }
      if (existing.some((u) => u.email.toLowerCase() === values.email.toLowerCase())) {
        setServerError("That email is already registered.");
        return;
      }
    }
    if (!USE_MOCKS) {
      await registerUser({
        first_name: values.firstName,
        last_name: values.lastName,
        username: values.username,
        email: values.email,
        phone: values.phone,
        employee_id: values.employeeId || null,
        role: "Employee",
        password: values.password,
      });
    } else {
      const user = await createUser({
        id: `U${Date.now()}`,
        firstName: values.firstName,
        lastName: values.lastName,
        username: values.username,
        email: values.email,
        phone: values.phone,
        employeeId: values.employeeId || null,
        role: "Employee",
        status: "Active",
        avatarColor: "bg-blue-500",
      });
      setUserPassword(user.id, values.password);
    }
    navigate("/login", { replace: true, state: { registered: true } });
  }

  return (
    <div className="min-h-screen bg-bg px-4 py-8 sm:px-6">
      <div className="mx-auto max-w-3xl">
        <div className="mb-6 flex items-center gap-2.5">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-white"><ShieldHalf className="h-5 w-5" /></div>
          <div><p className="font-display text-lg font-bold text-text">EPMS</p><p className="text-xs text-text-muted">Employee Payroll Management System</p></div>
        </div>
        <div className="rounded-2xl border border-border bg-white p-6 shadow-card sm:p-8">
          <div className="mb-6"><h1 className="font-display text-2xl font-semibold text-text">Create an account</h1><p className="mt-1 text-sm text-text-muted">Create an Employee account. Administrative roles are assigned through the authorized administration workflow.</p></div>
          {serverError && <div className="mb-5 rounded-lg border border-red-200 bg-danger-50 px-3 py-2 text-sm text-danger">{serverError}</div>}
          <form onSubmit={handleSubmit(onSubmit)} className="grid grid-cols-1 gap-4 sm:grid-cols-2" noValidate>
            {(["firstName", "lastName", "username", "email", "phone"] as const).map((field) => (
              <div key={field}>
                <Label required>{field === "firstName" ? "First Name" : field === "lastName" ? "Last Name" : field === "username" ? "Username" : field === "email" ? "Email" : "Phone"}</Label>
                <Input type={field === "email" ? "email" : "text"} {...register(field)} error={!!errors[field]} />
                {errors[field] && <p className="mt-1 text-xs text-danger">{errors[field]?.message}</p>}
              </div>
            ))}
            <div><Label>Employee ID</Label><Input placeholder="Optional" {...register("employeeId")} /></div>
            <div><Label required>Role</Label><Select {...register("role")} disabled><option value="Employee">Employee</option></Select><p className="mt-1 text-xs text-text-muted">Public registration creates Employee accounts. Administrative roles are assigned by authorized administrators.</p></div>
            <div><Label required>Password</Label><Input type="password" {...register("password")} error={!!errors.password} />{errors.password && <p className="mt-1 text-xs text-danger">{errors.password.message}</p>}</div>
            <div><Label required>Confirm Password</Label><Input type="password" {...register("confirmPassword")} error={!!errors.confirmPassword} />{errors.confirmPassword && <p className="mt-1 text-xs text-danger">{errors.confirmPassword.message}</p>}</div>
            <div className="sm:col-span-2 flex items-center justify-between pt-2">
              <Link to="/login" className="text-sm font-medium text-secondary hover:underline">Back to login</Link>
              <Button type="submit" loading={isSubmitting}><UserPlus className="h-4 w-4" /> Create Account</Button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
