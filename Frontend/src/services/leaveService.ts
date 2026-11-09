// FastAPI: GET/POST /leaves, GET /leaves/{id}, PUT /leaves/{id}/approve, PUT /leaves/{id}/reject
import { leaveRequests, leaveBalances } from "@/data/mockData";
import { createMockStore } from "./mockStore";
import { apiClient, mockDelay, USE_MOCKS } from "./api";
import type { LeaveRequest, LeaveBalance } from "@/types";

const store = createMockStore<LeaveRequest>(leaveRequests);
const list = <T,>(r: any): T[] => (Array.isArray(r) ? r : r?.items ?? r?.data ?? r?.results ?? []);

function normalizeLeaveRequest(l: any): LeaveRequest {
  return {
    id: String(l.id || (l.leave_request_id ? `LV${l.leave_request_id}` : `LV${Date.now()}`)),
    employeeId: String(l.employeeId || l.employee_id || ""),
    leaveType: (l.leaveType || l.leave_type || "Casual") as any,
    startDate: String(l.startDate || l.start_date || ""),
    endDate: String(l.endDate || l.end_date || ""),
    totalDays: Number(l.totalDays ?? l.total_days ?? 1),
    reason: String(l.reason || ""),
    status: (l.status || "Pending") as any,
    approverId: l.approverId ?? l.approver_id ?? null,
    appliedDate: String(l.appliedDate || l.applied_date || ""),
    approvalDate: l.approvalDate ?? l.approval_date ?? null,
  };
}

function normalizeLeaveBalance(b: any, _index: number, defaultEmpId?: string): LeaveBalance {
  return {
    employeeId: String(b.employeeId || b.employee_id || defaultEmpId || ""),
    leaveType: (b.leaveType || b.leave_type || "Casual") as any,
    entitled: Number(b.entitled ?? 0),
    used: Number(b.used ?? 0),
    balance: Number(b.balance ?? 0),
  };
}

export const listLeaves = async (): Promise<LeaveRequest[]> => {
  if (USE_MOCKS) return store.list();
  const res = await apiClient.get<any>("/leaves");
  return list<any>(res).map(normalizeLeaveRequest);
};

export const getLeave = async (id: string): Promise<LeaveRequest | null> => {
  if (USE_MOCKS) return (await store.get(id)) ?? null;
  const res = await apiClient.get<any>(`/leaves/${id}`);
  return res ? normalizeLeaveRequest(res) : null;
};

export const createLeave = async (x: LeaveRequest): Promise<LeaveRequest> => {
  if (USE_MOCKS) return store.create(x);
  const payload = {
    employeeId: x.employeeId,
    leaveType: x.leaveType,
    startDate: x.startDate,
    endDate: x.endDate,
    totalDays: x.totalDays,
    reason: x.reason,
    status: x.status,
  };
  const res = await apiClient.post<any>("/leaves", payload);
  return normalizeLeaveRequest(res);
};

export const approveLeave = async (id: string, approverId: string): Promise<LeaveRequest> => {
  if (USE_MOCKS) return store.update(id, { status: "Approved", approverId, approvalDate: new Date().toISOString().slice(0, 10) }) as any;
  const res = await apiClient.put<any>(`/leaves/${id}/approve`, { approverId });
  return normalizeLeaveRequest(res);
};

export const rejectLeave = async (id: string, approverId: string): Promise<LeaveRequest> => {
  if (USE_MOCKS) return store.update(id, { status: "Rejected", approverId, approvalDate: new Date().toISOString().slice(0, 10) }) as any;
  const res = await apiClient.put<any>(`/leaves/${id}/reject`, { approverId });
  return normalizeLeaveRequest(res);
};

export const cancelLeave = async (id: string): Promise<LeaveRequest> => {
  if (USE_MOCKS) return store.update(id, { status: "Cancelled" }) as any;
  const res = await apiClient.put<any>(`/leaves/${id}`, { status: "Cancelled" });
  return normalizeLeaveRequest(res);
};

export async function listLeaveBalances(employeeId?: string): Promise<LeaveBalance[]> {
  if (USE_MOCKS) {
    return mockDelay(employeeId ? leaveBalances.filter((b) => b.employeeId === employeeId) : leaveBalances);
  }
  const q = employeeId ? `?employee_id=${encodeURIComponent(employeeId)}` : "";
  const res = await apiClient.get<any>(`/leave-balances${q}`);
  return list<any>(res).map((b, idx) => normalizeLeaveBalance(b, idx, employeeId));
}
