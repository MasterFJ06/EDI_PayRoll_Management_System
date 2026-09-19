import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Dialog } from "@/components/ui/Dialog";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Select } from "@/components/ui/Select";
import { createUser, updateUser } from "@/services/userService";
import { ALL_ROLES } from "@/config/permissions";
import type { AppUser, Role } from "@/types";

const schema = z.object({
  firstName: z.string().min(1, "First name is required"),
  lastName: z.string().min(1, "Last name is required"),
  username: z.string().min(3, "Username must be at least 3 characters"),
  email: z.string().email("Enter a valid email address"),
  phone: z.string().min(10, "Enter a valid phone number"),
  employeeId: z.string().optional(),
  role: z.string().min(1, "Role is required"),
  status: z.enum(["Active", "Inactive"]),
  password: z.string().optional(),
  confirmPassword: z.string().optional(),
}).refine((d) => !d.password || d.password === d.confirmPassword, {
  message: "Passwords do not match", path: ["confirmPassword"],
}).refine((d) => !d.password || d.password.length >= 8, {
  message: "Password must be at least 8 characters", path: ["password"],
});
type FormValues = z.infer<typeof schema>;

export function UserFormDialog({ open, onClose, user, onSaved }: { open: boolean; onClose: () => void; user: AppUser | null; onSaved: () => void }) {
  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { status: "Active", role: "Employee" },
  });

  useEffect(() => {
    if (open) {
      reset(user ? {
        firstName: user.firstName, lastName: user.lastName, username: user.username, email: user.email,
        phone: user.phone, employeeId: user.employeeId ?? "", role: user.role, status: user.status,
        password: "", confirmPassword: "",
      } : { firstName: "", lastName: "", username: "", email: "", phone: "", employeeId: "", role: "Employee", status: "Active", password: "", confirmPassword: "" });
    }
  }, [open, user, reset]);

  async function onSubmit(values: FormValues) {
    if (user) {
      await updateUser(user.id, { ...values, role: values.role as Role, employeeId: values.employeeId || null });
    } else {
      await createUser({
        id: `U${Date.now()}`, avatarColor: "bg-blue-500",
        ...values, role: values.role as Role, employeeId: values.employeeId || null,
      });
    }
    onSaved();
  }

  return (
    <Dialog
      open={open} onClose={onClose}
      title={user ? "Edit User" : "Add New User"}
      description="User accounts authenticate against the FastAPI /auth endpoints using JWT."
      size="lg"
      footer={
        <>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={handleSubmit(onSubmit)} loading={isSubmitting}>{user ? "Save Changes" : "Create User"}</Button>
        </>
      }
    >
      <form className="grid grid-cols-1 gap-4 sm:grid-cols-2" onSubmit={handleSubmit(onSubmit)}>
        <div>
          <Label required>First Name</Label>
          <Input {...register("firstName")} error={!!errors.firstName} />
          {errors.firstName && <p className="mt-1 text-xs text-danger">{errors.firstName.message}</p>}
        </div>
        <div>
          <Label required>Last Name</Label>
          <Input {...register("lastName")} error={!!errors.lastName} />
          {errors.lastName && <p className="mt-1 text-xs text-danger">{errors.lastName.message}</p>}
        </div>
        <div>
          <Label required>Username</Label>
          <Input {...register("username")} error={!!errors.username} />
          {errors.username && <p className="mt-1 text-xs text-danger">{errors.username.message}</p>}
        </div>
        <div>
          <Label required>Email</Label>
          <Input type="email" {...register("email")} error={!!errors.email} />
          {errors.email && <p className="mt-1 text-xs text-danger">{errors.email.message}</p>}
        </div>
        <div>
          <Label required>Phone</Label>
          <Input {...register("phone")} error={!!errors.phone} />
          {errors.phone && <p className="mt-1 text-xs text-danger">{errors.phone.message}</p>}
        </div>
        <div>
          <Label>Employee ID</Label>
          <Input placeholder="e.g. EMP004 (optional)" {...register("employeeId")} />
        </div>
        <div>
          <Label required>Role</Label>
          <Select {...register("role")}>
            {ALL_ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
          </Select>
        </div>
        <div>
          <Label required>Status</Label>
          <Select {...register("status")}>
            <option value="Active">Active</option>
            <option value="Inactive">Inactive</option>
          </Select>
        </div>
        <div>
          <Label>{user ? "New Password (optional)" : "Password"}</Label>
          <Input type="password" {...register("password")} error={!!errors.password} />
          {errors.password && <p className="mt-1 text-xs text-danger">{errors.password.message}</p>}
        </div>
        <div>
          <Label>Confirm Password</Label>
          <Input type="password" {...register("confirmPassword")} error={!!errors.confirmPassword} />
          {errors.confirmPassword && <p className="mt-1 text-xs text-danger">{errors.confirmPassword.message}</p>}
        </div>
      </form>
    </Dialog>
  );
}
