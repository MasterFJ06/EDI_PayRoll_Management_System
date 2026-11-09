import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Dialog } from "@/components/ui/Dialog";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Select } from "@/components/ui/Select";
import { Textarea } from "@/components/ui/Textarea";
import { createEmployee, updateEmployee, listEmployees } from "@/services/employeeService";
import { listDepartments } from "@/services/departmentService";
import { listDesignations } from "@/services/designationService";
import type { Department, Designation, Employee } from "@/types";

const schema = z.object({
  firstName: z.string().min(1, "First name is required"),
  lastName: z.string().min(1, "Last name is required"),
  email: z.string().email("Enter a valid email address"),
  phone: z.string().min(10, "Enter a valid phone number"),
  dateOfBirth: z.string().min(1, "Date of birth is required"),
  gender: z.enum(["Male", "Female", "Other"]),
  departmentId: z.string().min(1, "Department is required"),
  designationId: z.string().min(1, "Designation is required"),
  managerId: z.string().optional(),
  employmentType: z.enum(["Full-Time", "Part-Time", "Contract", "Intern"]),
  joiningDate: z.string().min(1, "Joining date is required"),
  employmentStatus: z.enum(["Active", "On Leave", "Suspended", "Terminated"]),
  address: z.string().min(1, "Address is required"),
  emergencyContact: z.string().min(10, "Enter a valid contact number"),
});
type FormValues = z.infer<typeof schema>;

export interface EmployeeFormDialogProps {
  open: boolean;
  onClose: () => void;
  employee: Employee | null;
  onSaved: () => void;
  departments?: Department[];
  designations?: Designation[];
  employees?: Employee[];
}

export function EmployeeFormDialog({
  open,
  onClose,
  employee,
  onSaved,
  departments: departmentsProp,
  designations: designationsProp,
  employees: employeesProp,
}: EmployeeFormDialogProps) {
  const [departmentsList, setDepartmentsList] = useState<Department[]>(departmentsProp ?? []);
  const [designationsList, setDesignationsList] = useState<Designation[]>(designationsProp ?? []);
  const [employeesList, setEmployeesList] = useState<Employee[]>(employeesProp ?? []);

  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { gender: "Male", employmentType: "Full-Time", employmentStatus: "Active" },
  });

  useEffect(() => {
    if (departmentsProp) setDepartmentsList(departmentsProp);
    if (designationsProp) setDesignationsList(designationsProp);
    if (employeesProp) setEmployeesList(employeesProp);

    if (open && (!departmentsProp || !designationsProp || !employeesProp)) {
      Promise.all([
        departmentsProp ? Promise.resolve(departmentsProp) : listDepartments(),
        designationsProp ? Promise.resolve(designationsProp) : listDesignations(),
        employeesProp ? Promise.resolve(employeesProp) : listEmployees(),
      ]).then(([depts, desigs, emps]) => {
        setDepartmentsList(depts);
        setDesignationsList(desigs);
        setEmployeesList(emps);
      }).catch(() => {
        // Fallback or ignore
      });
    }
  }, [open, departmentsProp, designationsProp, employeesProp]);

  useEffect(() => {
    if (open) {
      const defaultDeptId = employee?.departmentId ?? departmentsList[0]?.id ?? "";
      const defaultDesigId = employee?.designationId ?? designationsList[0]?.id ?? "";
      reset(employee ? {
        firstName: employee.firstName, lastName: employee.lastName, email: employee.email, phone: employee.phone,
        dateOfBirth: employee.dateOfBirth, gender: employee.gender, departmentId: employee.departmentId,
        designationId: employee.designationId, managerId: employee.managerId ?? "", employmentType: employee.employmentType,
        joiningDate: employee.joiningDate, employmentStatus: employee.employmentStatus, address: employee.address,
        emergencyContact: employee.emergencyContact,
      } : {
        firstName: "", lastName: "", email: "", phone: "", dateOfBirth: "", gender: "Male",
        departmentId: defaultDeptId, designationId: defaultDesigId, managerId: "",
        employmentType: "Full-Time", joiningDate: new Date().toISOString().slice(0, 10),
        employmentStatus: "Active", address: "", emergencyContact: "",
      });
    }
  }, [open, employee, reset, departmentsList, designationsList]);

  async function onSubmit(values: FormValues) {
    const today = new Date().toISOString().slice(0, 10);
    if (employee) {
      await updateEmployee(employee.id, { ...values, managerId: values.managerId || null, updatedDate: today });
    } else {
      let nextNum = employeesList.length + 1;
      employeesList.forEach((e) => {
        const num = parseInt(e.employeeCode?.replace(/\D/g, "") || "0", 10);
        if (num >= nextNum) nextNum = num + 1;
      });
      const code = `EMP${String(nextNum).padStart(3, "0")}`;
      await createEmployee({
        id: code, employeeCode: code, ...values, managerId: values.managerId || null,
        createdDate: today, updatedDate: today,
      });
    }
    onSaved();
  }

  return (
    <Dialog
      open={open} onClose={onClose}
      title={employee ? "Edit Employee" : "Add New Employee"} size="xl"
      description="Employees become eligible for payroll once a salary structure is assigned."
      footer={<>
        <Button variant="outline" onClick={onClose}>Cancel</Button>
        <Button onClick={handleSubmit(onSubmit)} loading={isSubmitting}>{employee ? "Save Changes" : "Add Employee"}</Button>
      </>}
    >
      <form className="grid grid-cols-1 gap-4 sm:grid-cols-2" onSubmit={handleSubmit(onSubmit)}>
        <div><Label required>First Name</Label><Input {...register("firstName")} error={!!errors.firstName} />{errors.firstName && <p className="mt-1 text-xs text-danger">{errors.firstName.message}</p>}</div>
        <div><Label required>Last Name</Label><Input {...register("lastName")} error={!!errors.lastName} />{errors.lastName && <p className="mt-1 text-xs text-danger">{errors.lastName.message}</p>}</div>
        <div><Label required>Email</Label><Input type="email" {...register("email")} error={!!errors.email} />{errors.email && <p className="mt-1 text-xs text-danger">{errors.email.message}</p>}</div>
        <div><Label required>Phone</Label><Input {...register("phone")} error={!!errors.phone} />{errors.phone && <p className="mt-1 text-xs text-danger">{errors.phone.message}</p>}</div>
        <div><Label required>Date of Birth</Label><Input type="date" {...register("dateOfBirth")} error={!!errors.dateOfBirth} /></div>
        <div><Label required>Gender</Label><Select {...register("gender")}><option>Male</option><option>Female</option><option>Other</option></Select></div>
        <div>
          <Label required>Department</Label>
          <Select {...register("departmentId")} error={!!errors.departmentId}>
            {departmentsList.length === 0 ? (
              <option value="">No departments available</option>
            ) : (
              departmentsList.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)
            )}
          </Select>
          {errors.departmentId && <p className="mt-1 text-xs text-danger">{errors.departmentId.message}</p>}
        </div>
        <div>
          <Label required>Designation</Label>
          <Select {...register("designationId")} error={!!errors.designationId}>
            {designationsList.length === 0 ? (
              <option value="">No designations available</option>
            ) : (
              designationsList.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)
            )}
          </Select>
          {errors.designationId && <p className="mt-1 text-xs text-danger">{errors.designationId.message}</p>}
        </div>
        <div>
          <Label>Manager</Label>
          <Select {...register("managerId")}>
            <option value="">No Manager</option>
            {employeesList
              .filter((e) => !employee || e.id !== employee.id)
              .map((e) => <option key={e.id} value={e.id}>{e.firstName} {e.lastName} ({e.employeeCode})</option>)}
          </Select>
        </div>
        <div><Label required>Employment Type</Label><Select {...register("employmentType")}><option>Full-Time</option><option>Part-Time</option><option>Contract</option><option>Intern</option></Select></div>
        <div><Label required>Joining Date</Label><Input type="date" {...register("joiningDate")} /></div>
        <div><Label required>Employment Status</Label><Select {...register("employmentStatus")}><option>Active</option><option>On Leave</option><option>Suspended</option><option>Terminated</option></Select></div>
        <div className="sm:col-span-2"><Label required>Address</Label><Textarea rows={2} {...register("address")} />{errors.address && <p className="mt-1 text-xs text-danger">{errors.address.message}</p>}</div>
        <div className="sm:col-span-2"><Label required>Emergency Contact</Label><Input {...register("emergencyContact")} error={!!errors.emergencyContact} />{errors.emergencyContact && <p className="mt-1 text-xs text-danger">{errors.emergencyContact.message}</p>}</div>
      </form>
    </Dialog>
  );
}
