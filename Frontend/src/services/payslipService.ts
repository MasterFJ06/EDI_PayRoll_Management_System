// FastAPI: GET /payslips, GET /payslips/{id}, GET /payslips/{id}/pdf
import { payslips } from "@/data/mockData";
import { createMockStore } from "./mockStore";
import { apiClient, mockDelay, USE_MOCKS, API_BASE_URL } from "./api";
import type { Payslip } from "@/types";

const store = createMockStore<Payslip>(payslips);
const list = <T,>(r: any): T[] => (Array.isArray(r) ? r : r?.items ?? r?.data ?? r?.results ?? []);

export const listPayslips = async (): Promise<Payslip[]> =>
  USE_MOCKS ? store.list() : list<Payslip>(await apiClient.get<any>("/payslips"));

export const getPayslip = async (id: string) =>
  USE_MOCKS ? store.get(id) : apiClient.get<Payslip>(`/payslips/${id}`);

export async function generatePayslip(payslip: Payslip) {
  return USE_MOCKS ? store.create(payslip) : apiClient.post<Payslip>("/payslips", payslip);
}

export async function downloadPayslipPdf(id: string): Promise<void> {
  if (USE_MOCKS) {
    await mockDelay(null, 200);
    const p = await store.get(id);
    if (!p) throw new Error("Payslip not found.");
    const blob = new Blob(
      [
        `==========================================================\n` +
          `           EMPLOYEE PAYROLL MANAGEMENT SYSTEM             \n` +
          `                    SALARY PAYSLIP                        \n` +
          `==========================================================\n\n` +
          `Payslip ID    : ${p.id}\n` +
          `Payroll Month : ${p.payrollMonth}\n` +
          `Employee ID   : ${p.employeeId}\n` +
          `Basic Salary  : ₹${p.basicSalary.toLocaleString("en-IN")}\n` +
          `Allowances    : ₹${p.allowances.toLocaleString("en-IN")}\n` +
          `Gross Salary  : ₹${p.grossSalary.toLocaleString("en-IN")}\n` +
          `Deductions    : ₹${p.deductions.toLocaleString("en-IN")}\n` +
          `Net Salary    : ₹${p.netSalary.toLocaleString("en-IN")}\n` +
          `Status        : ${p.status}\n` +
          `Signed By     : ${p.digitalSignature}\n`,
      ],
      { type: "application/pdf" }
    );
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${id}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
    return;
  }

  const token = localStorage.getItem("epms_access_token") ?? sessionStorage.getItem("epms_access_token");
  const res = await fetch(`${API_BASE_URL}/payslips/${encodeURIComponent(id)}/pdf`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  if (!res.ok) {
    let errDetail = `Unable to download payslip PDF (${res.status}).`;
    try {
      const errJson = await res.json();
      if (errJson?.detail) errDetail = errJson.detail;
    } catch {}
    throw new Error(errDetail);
  }

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${id}.pdf`;
  a.click();
  URL.revokeObjectURL(url);
}
