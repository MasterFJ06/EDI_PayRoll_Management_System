export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
}

export interface HealthResponse {
  status: string;
  service: string;
}

export type PayrollRunStatus = "CREATED" | "PROCESSING" | "FAILED" | "PROCESSED" | "FINALIZED";
export interface PayrollRun {
  payroll_run_id: number;
  payroll_year: number;
  payroll_month: number;
  status: PayrollRunStatus;
  initiated_by_user_id: number;
}
export interface PayrollRunCreateRequest { year: number; month: number }
export interface FinalizedPayrollSummary {
  payroll_run_id: number; payroll_year: number; payroll_month: number; status: "FINALIZED";
  initiated_by_user_id: number; employee_result_count: number;
  total_gross_pay: number | string; total_deductions: number | string; total_net_pay: number | string;
}
export interface PayrollResultReportRow {
  payroll_result_id: number; payroll_run_id: number; employee_id: number; salary_assignment_id: number;
  gross_earnings: number | string; total_deductions: number | string; net_salary: number | string;
  employee_code: string | null; employee_name: string | null;
}
export interface PayrollResultReportPage {
  payroll_run_id: number; results: PayrollResultReportRow[];
  pagination: { limit: number; has_more: boolean; next_cursor: string | null };
}
export interface PayrollComponentReportRow {
  payroll_result_component_id: number; payroll_run_id: number; payroll_result_id: number; employee_id: number;
  employee_code: string | null; employee_name: string | null; salary_component_id: number;
  component_code: string; component_name: string; component_type: "EARNING" | "DEDUCTION";
  amount: number | string; calculation_order: number;
}
export interface PayrollComponentReportPage {
  payroll_run_id: number; components: PayrollComponentReportRow[];
  pagination: { limit: number; has_more: boolean; next_cursor: string | null };
}
export interface PayslipCreateResponse {
  payslip_id: number;
  payroll_result_id: number;
  payslip_number: string;
  generated_by_user_id: number;
  generated_at: string;
  document_path: string | null;
}

export interface EmployeeReportRow {
  employee_id: number;
  employee_code: string;
  first_name: string;
  last_name: string;
  department_id: number;
  department_name: string | null;
  designation_id: number;
  designation_name: string | null;
  joining_date: string;
  employment_end_date: string | null;
  employment_status: "ACTIVE" | "INACTIVE" | "TERMINATED";
}

export interface EmployeeReportPage {
  employees: EmployeeReportRow[];
  pagination: { limit: number; has_more: boolean; next_cursor: string | null };
}

export interface EmployeeCreateRequest {
  employee_code: string;
  user_id?: number;
  first_name: string;
  last_name: string;
  department_id: number;
  designation_id: number;
  manager_employee_id?: number;
  joining_date: string;
  employment_end_date?: string;
}

export interface EmployeeCreateResponse extends Omit<EmployeeCreateRequest, "user_id" | "manager_employee_id" | "employment_end_date"> {
  employee_id: number;
  user_id: number | null;
  manager_employee_id: number | null;
  employment_end_date: string | null;
  employment_status: "ACTIVE" | "INACTIVE" | "TERMINATED";
}

export type AttendanceStatus = "PRESENT" | "ABSENT" | "HALF_DAY" | "ON_LEAVE" | "HOLIDAY";
export interface AttendanceReportRow {
  attendance_id: number; employee_id: number; employee_code: string; first_name: string; last_name: string;
  department_id: number; department_name: string | null; designation_id: number; designation_name: string | null;
  attendance_date: string; attendance_status: AttendanceStatus; check_in_time: string | null; check_out_time: string | null;
}
export interface AttendanceReportPage {
  attendance_records: AttendanceReportRow[];
  pagination: { limit: number; has_more: boolean; next_cursor: string | null };
}
export interface AttendanceCreateRequest {
  employee_id: number; attendance_date: string; check_in_time: string | null; check_out_time: string | null; attendance_status: AttendanceStatus;
}
export interface AttendanceCreateResponse extends AttendanceCreateRequest { attendance_id: number }

export type LeaveStatus = "PENDING" | "APPROVED" | "REJECTED" | "CANCELLED";
export interface LeaveAllocationRow {
  leave_request_id: number; leave_request_day_id: number; employee_id: number; employee_code: string;
  first_name: string; last_name: string; department_id: number; department_name: string; designation_id: number;
  designation_name: string; leave_type_id: number; leave_type_name: string; start_date: string; end_date: string;
  requested_days: number | string; status: LeaveStatus; leave_date: string; day_fraction: number | string;
}
export interface LeaveAllocationPage {
  allocations: LeaveAllocationRow[];
  pagination: { limit: number; has_more: boolean; next_cursor: string | null };
}
export interface LeaveBalanceRow {
  employee_id: number; employee_code: string; first_name: string; last_name: string; department_id: number;
  department_name: string; designation_id: number; designation_name: string; leave_type_id: number;
  leave_type_name: string; balance_year: number; allocated_days: number | string; used_days: number | string;
}
export interface LeaveBalancePage {
  balances: LeaveBalanceRow[];
  pagination: { limit: number; has_more: boolean; next_cursor: string | null };
}
export interface LeaveRequestCreateRequest {
  employee_id: number; leave_type_id: number; start_date: string; end_date: string;
  requested_days: string; reason?: string; allocations: { leave_date: string; day_fraction: string }[];
}
export interface LeaveRequestResponse {
  leave_request_id: number; employee_id: number; leave_type_id: number; start_date: string; end_date: string;
  requested_days: number | string; reason: string | null; status: LeaveStatus; reviewed_by_employee_id: number | null;
  reviewed_at: string | null; review_comment: string | null; allocations: { leave_date: string; day_fraction: number | string }[];
}
export interface LeaveBalanceCreateRequest {
  employee_id: number; leave_type_id: number; balance_year: number; allocated_days: string; used_days: string;
}
export interface LeaveBalanceCreateResponse extends LeaveBalanceCreateRequest { leave_balance_id: number }

export type CompensationStatus = "ACTIVE" | "INACTIVE";
export interface SalaryStructureCreateRequest { structure_code: string; structure_name: string; description?: string | null; status?: CompensationStatus }
export interface SalaryStructureResponse extends SalaryStructureCreateRequest { salary_structure_id: number; description: string | null; status: CompensationStatus }
export type SalaryComponentType = "EARNING" | "DEDUCTION";
export interface SalaryComponentCreateRequest { component_code: string; component_name: string; component_type: SalaryComponentType; status?: CompensationStatus }
export interface SalaryComponentResponse extends SalaryComponentCreateRequest { salary_component_id: number; status: CompensationStatus }
export interface SalaryRevisionCreateRequest { salary_structure_id: number; revision_number: number; effective_from: string; effective_to?: string | null }
export interface SalaryRevisionResponse extends SalaryRevisionCreateRequest { salary_revision_id: number; effective_to: string | null }
export type CalculationType = "FIXED" | "PERCENTAGE";
export interface SalaryRevisionComponentCreateRequest {
  salary_revision_id: number; salary_component_id: number; calculation_type: CalculationType;
  fixed_amount: string | null; percentage_value: string | null; base_component_id: number | null; is_overtime_base: boolean;
}
export interface SalaryRevisionComponentResponse extends SalaryRevisionComponentCreateRequest {}
export interface EmployeeSalaryAssignmentCreateRequest { employee_id: number; salary_revision_id: number; effective_from: string; effective_to?: string | null }
export interface EmployeeSalaryAssignmentResponse extends EmployeeSalaryAssignmentCreateRequest { salary_assignment_id: number; effective_to: string | null }

interface ApiErrorBody {
  detail?: string | Array<{ msg?: string }>;
  error?: { message?: string };
}

export class ApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message);
    this.name = "ApiError";
  }
}

class ApiClient {
  private readonly baseUrl = (
    import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1"
  ).replace(/\/$/, "");
  private tokens: TokenPair | null = null;
  private refreshInFlight: Promise<TokenPair | null> | null = null;
  private onSessionExpired: (() => void) | null = null;

  hasSession(): boolean {
    return this.tokens !== null;
  }

  setTokens(tokens: TokenPair | null): void {
    this.tokens = tokens;
  }

  setSessionExpiredHandler(handler: (() => void) | null): void {
    this.onSessionExpired = handler;
  }

  async login(username: string, password: string): Promise<TokenPair> {
    const response = await fetch(`${this.baseUrl}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const body = await this.readResponse<TokenPair>(response);
    if (
      typeof body.access_token !== "string" ||
      typeof body.refresh_token !== "string" ||
      body.token_type !== "bearer"
    ) {
      throw new ApiError("The sign-in response was invalid.", response.status);
    }
    return body;
  }

  get<T>(path: string, authenticated = true): Promise<T> {
    return this.request<T>(path, { method: "GET" }, authenticated);
  }

  post<T>(path: string, body: unknown, authenticated = true): Promise<T> {
    return this.request<T>(
      path,
      { method: "POST", body: JSON.stringify(body) },
      authenticated,
    );
  }

  createPayrollRun(body: PayrollRunCreateRequest): Promise<PayrollRun> {
    return this.post<PayrollRun>("/payroll/runs", body);
  }

  getPayrollRun(runId: number): Promise<PayrollRun> {
    return this.get<PayrollRun>(`/payroll/runs/${runId}`);
  }

  payrollRunAction(runId: number, action: "process" | "retry" | "recover" | "finalize"): Promise<PayrollRun> {
    return this.post<PayrollRun>(`/payroll/runs/${runId}/${action}`, undefined);
  }

  createPayslip(runId: number, resultId: number, payslipNumber: string): Promise<PayslipCreateResponse> {
    return this.post<PayslipCreateResponse>(`/payroll/runs/${runId}/results/${resultId}/payslip`, { payslip_number: payslipNumber });
  }

  async logout(): Promise<boolean> {
    const refreshToken = this.tokens?.refresh_token;
    let revocationConfirmed = !refreshToken;
    try {
      if (refreshToken) {
        const response = await fetch(`${this.baseUrl}/auth/logout`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
        revocationConfirmed = response.status === 204;
      }
    } catch {
      // End the local session even if the server could not confirm revocation.
    } finally {
      this.clearSession();
    }
    return revocationConfirmed;
  }

  private async request<T>(
    path: string,
    init: RequestInit,
    authenticated: boolean,
    mayRefresh = true,
  ): Promise<T> {
    const response = await this.fetchWithCurrentToken(path, init, authenticated);
    if (response.status === 401 && authenticated && mayRefresh) {
      const replacement = await this.refresh();
      if (!replacement) {
        this.clearSession();
        throw new ApiError("Your session could not be renewed. Sign in again to continue.", 401);
      }
      const retried = await this.fetchWithCurrentToken(path, init, true);
      if (retried.status === 401) {
        this.clearSession();
        throw new ApiError("Your session has expired. Please sign in again.", 401);
      }
      return this.readResponse<T>(retried);
    }
    return this.readResponse<T>(response);
  }

  private async fetchWithCurrentToken(
    path: string,
    init: RequestInit,
    authenticated: boolean,
  ): Promise<Response> {
    const headers = new Headers(init.headers);
    if (init.body && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
    if (authenticated && this.tokens) {
      headers.set("Authorization", `Bearer ${this.tokens.access_token}`);
    }
    return fetch(`${this.baseUrl}${path}`, { ...init, headers });
  }

  private refresh(): Promise<TokenPair | null> {
    if (this.refreshInFlight) return this.refreshInFlight;
    const refreshToken = this.tokens?.refresh_token;
    if (!refreshToken) return Promise.resolve(null);

    this.refreshInFlight = (async () => {
      try {
        const response = await fetch(`${this.baseUrl}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
        const body = await this.readResponse<TokenPair>(response);
        if (
          typeof body.access_token !== "string" ||
          typeof body.refresh_token !== "string" ||
          body.token_type !== "bearer"
        ) {
          return null;
        }
        this.tokens = body;
        return body;
      } catch {
        return null;
      } finally {
        this.refreshInFlight = null;
      }
    })();
    return this.refreshInFlight;
  }

  private clearSession(): void {
    this.tokens = null;
    this.onSessionExpired?.();
  }

  private async readResponse<T>(response: Response): Promise<T> {
    if (response.status === 204) return undefined as T;
    const body = (await response.json().catch(() => null)) as
      | T
      | ApiErrorBody
      | null;
    if (!response.ok) {
      const errorBody = body as ApiErrorBody | null;
      const detail = errorBody?.detail;
      const message =
        typeof detail === "string"
          ? detail
          : Array.isArray(detail)
            ? detail.map((item) => item.msg).filter(Boolean).join(" ")
            : typeof errorBody?.error?.message === "string"
              ? errorBody.error.message
            : "The request could not be completed.";
      throw new ApiError(message, response.status);
    }
    return body as T;
  }
}

export const apiClient = new ApiClient();
