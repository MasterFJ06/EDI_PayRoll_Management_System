// FastAPI: GET /reports/salary, GET /reports/leave, GET /reports/payroll, GET/POST /exports
import { reportExports, leaveAlerts } from "@/data/mockData"; import { createMockStore } from "./mockStore"; import { apiClient, mockDelay, USE_MOCKS } from "./api"; import type { ReportExport, LeaveAlert } from "@/types";
const store=createMockStore<ReportExport>(reportExports); const list=<T,>(r:any):T[]=>Array.isArray(r)?r:r?.items??r?.data??r?.results??[];
export const listExports=async():Promise<ReportExport[]>=>USE_MOCKS?store.list():list<ReportExport>(await apiClient.get<any>("/exports"));
export async function requestExport(exp:ReportExport){return USE_MOCKS?store.create(exp):apiClient.post<ReportExport>("/exports",exp);}
export async function listLeaveAlerts():Promise<LeaveAlert[]> {return USE_MOCKS?mockDelay(leaveAlerts):list<LeaveAlert>(await apiClient.get<any>("/reports/leave"));}
export async function getSalaryReport<T=unknown>(params?:Record<string,string|number|undefined>):Promise<T>{if(USE_MOCKS)return [] as T;const q=new URLSearchParams();Object.entries(params??{}).forEach(([k,v])=>v!==undefined&&q.set(k,String(v)));return apiClient.get<T>(`/reports/salary${q.size?`?${q}`:""}`);}
export async function getPayrollReport<T=unknown>(params?:Record<string,string|number|undefined>):Promise<T>{if(USE_MOCKS)return [] as T;const q=new URLSearchParams();Object.entries(params??{}).forEach(([k,v])=>v!==undefined&&q.set(k,String(v)));return apiClient.get<T>(`/reports/payroll${q.size?`?${q}`:""}`);}
