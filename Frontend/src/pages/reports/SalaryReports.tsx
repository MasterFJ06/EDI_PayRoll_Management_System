import { useState } from "react";
import { BarChart3, Download, FileSpreadsheet, FileText as FileIcon, RotateCcw } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { Card, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import { Label } from "@/components/ui/Label";
import { DashboardCard } from "@/components/common/DashboardCard";
import { ChartCard } from "@/components/common/ChartCard";
import { departments, employees, salaryStructures, departmentName } from "@/data/mockData";
import { computeGross, computeDeductions } from "@/services/salaryService";
import { formatINR } from "@/utils/format";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from "recharts";

export default function SalaryReports() {
  const [department, setDepartment] = useState("all");
  const [employmentType, setEmploymentType] = useState("all");
  const [generated, setGenerated] = useState(true);

  const scopedEmployees = employees.filter((e) =>
    (department === "all" || e.departmentId === department) &&
    (employmentType === "all" || e.employmentType === employmentType)
  );
  const scopedIds = new Set(scopedEmployees.map((e) => e.id));
  const scopedStructures = salaryStructures.filter((s) => scopedIds.has(s.employeeId));

  const grossTotal = scopedStructures.reduce((s, x) => s + computeGross(x), 0);
  const deductionsTotal = scopedStructures.reduce((s, x) => s + computeDeductions(x), 0);
  const netTotal = grossTotal - deductionsTotal;

  const byDept = departments.map((d) => {
    const ids = new Set(employees.filter((e) => e.departmentId === d.id).map((e) => e.id));
    const structs = salaryStructures.filter((s) => ids.has(s.employeeId));
    return { name: d.code, gross: structs.reduce((s, x) => s + computeGross(x), 0), net: structs.reduce((s, x) => s + (computeGross(x) - computeDeductions(x)), 0) };
  });

  return (
    <div>
      <PageHeader title="Salary Reports" description="Generate and export salary reports filtered by department, designation and employment type." icon={<BarChart3 className="h-5 w-5" />} />

      <Card className="mb-6">
        <CardContent>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <div><Label>Reporting Period</Label><Select defaultValue="2026-08"><option value="2026-08">August 2026</option><option value="2026-07">July 2026</option></Select></div>
            <div><Label>Department</Label><Select value={department} onChange={(e) => setDepartment(e.target.value)}><option value="all">All Departments</option>{departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}</Select></div>
            <div><Label>Employment Type</Label><Select value={employmentType} onChange={(e) => setEmploymentType(e.target.value)}><option value="all">All Types</option><option>Full-Time</option><option>Part-Time</option><option>Contract</option><option>Intern</option></Select></div>
            <div className="flex items-end gap-2 lg:col-span-2">
              <Button onClick={() => setGenerated(true)} className="flex-1"><RotateCcw className="h-4 w-4" /> Generate Report</Button>
              <Button variant="outline" onClick={() => { setDepartment("all"); setEmploymentType("all"); }}>Reset</Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {generated && (
        <>
          <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <DashboardCard label="Total Employees" value={String(scopedEmployees.length)} icon={<BarChart3 className="h-[18px] w-[18px]" />} tone="primary" />
            <DashboardCard label="Gross Salary" value={formatINR(grossTotal)} icon={<BarChart3 className="h-[18px] w-[18px]" />} tone="info" />
            <DashboardCard label="Total Deductions" value={formatINR(deductionsTotal)} icon={<BarChart3 className="h-[18px] w-[18px]" />} tone="warning" />
            <DashboardCard label="Net Salary" value={formatINR(netTotal)} icon={<BarChart3 className="h-[18px] w-[18px]" />} tone="success" />
          </div>

          <ChartCard title="Gross vs Net Salary by Department" subtitle={department === "all" ? "All departments" : departmentName(department)}
            action={
              <div className="flex gap-1.5">
                <Button variant="outline" size="sm"><FileIcon className="h-3.5 w-3.5" /> PDF</Button>
                <Button variant="outline" size="sm"><FileSpreadsheet className="h-3.5 w-3.5" /> Excel</Button>
                <Button variant="outline" size="sm"><Download className="h-3.5 w-3.5" /> CSV</Button>
              </div>
            }
          >
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={byDept}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#64748B" }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: "#64748B" }} axisLine={false} tickLine={false} tickFormatter={(v) => `${v / 100000}L`} />
                <Tooltip contentStyle={{ borderRadius: 8, borderColor: "#E2E8F0", fontSize: 12 }} formatter={(v) => formatINR(Number(v ?? 0))} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Bar dataKey="gross" name="Gross" fill="#1E3A8A" radius={[4, 4, 0, 0]} />
                <Bar dataKey="net" name="Net" fill="#2563EB" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        </>
      )}
    </div>
  );
}
