// FastAPI: GET/POST /leaves, GET /leaves/{id}, PUT /leaves/{id}/approve, PUT /leaves/{id}/reject
import { leaveRequests, leaveBalances } from "@/data/mockData"; import { createMockStore } from "./mockStore"; import { apiClient, mockDelay, USE_MOCKS } from "./api"; import type { LeaveRequest, LeaveBalance } from "@/types";
const store=createMockStore<LeaveRequest>(leaveRequests); const list=<T,>(r:any):T[]=>Array.isArray(r)?r:r?.items??r?.data??r?.results??[];
export const listLeaves=async():Promise<LeaveRequest[]>=>USE_MOCKS?store.list():list<LeaveRequest>(await apiClient.get<any>("/leaves"));
export const getLeave=async(id:string)=>USE_MOCKS?store.get(id):apiClient.get<LeaveRequest>(`/leaves/${id}`);
export const createLeave=async(x:LeaveRequest)=>USE_MOCKS?store.create(x):apiClient.post<LeaveRequest>("/leaves",x);
export const approveLeave=async(id:string,approverId:string)=>USE_MOCKS?store.update(id,{status:"Approved",approverId,approvalDate:new Date().toISOString().slice(0,10)}):apiClient.put<LeaveRequest>(`/leaves/${id}/approve`,{approverId});
export const rejectLeave=async(id:string,approverId:string)=>USE_MOCKS?store.update(id,{status:"Rejected",approverId,approvalDate:new Date().toISOString().slice(0,10)}):apiClient.put<LeaveRequest>(`/leaves/${id}/reject`,{approverId});
export const cancelLeave=async(id:string)=>USE_MOCKS?store.update(id,{status:"Cancelled"}):apiClient.put<LeaveRequest>(`/leaves/${id}`,{status:"Cancelled"});
export async function listLeaveBalances(employeeId?:string):Promise<LeaveBalance[]> { if(USE_MOCKS) return mockDelay(employeeId?leaveBalances.filter(b=>b.employeeId===employeeId):leaveBalances); const q=employeeId?`?employee_id=${encodeURIComponent(employeeId)}`:""; return list<LeaveBalance>(await apiClient.get<any>(`/leave-balances${q}`)); }
