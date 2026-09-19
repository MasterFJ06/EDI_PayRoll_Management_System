// FastAPI: GET /payroll, POST /payroll/process, POST /payroll/validate, POST /payroll/{id}/approve
import { payrollRecords, payrollValidationIssues } from "@/data/mockData"; import { createMockStore } from "./mockStore"; import { apiClient, mockDelay, USE_MOCKS } from "./api"; import type { PayrollRecord, PayrollValidationIssue } from "@/types";
const store=createMockStore<PayrollRecord>(payrollRecords); const list=<T,>(r:any):T[]=>Array.isArray(r)?r:r?.items??r?.data??r?.results??[];
export const listPayroll=async():Promise<PayrollRecord[]>=>USE_MOCKS?store.list():list<PayrollRecord>(await apiClient.get<any>("/payroll"));
export const getPayroll=async(id:string)=>USE_MOCKS?store.get(id):apiClient.get<PayrollRecord>(`/payroll/${id}`);
export async function processPayrollMonth(month:string){ if(USE_MOCKS){const all=await store.list();const rows=all.filter(p=>p.payrollMonth===month);for(const p of rows)await store.update(p.id,{status:"Processed"});return mockDelay(rows.length,700);} return apiClient.post<number>("/payroll/process",{payrollMonth:month}); }
export async function approvePayroll(id:string){return USE_MOCKS?store.update(id,{status:"Approved"}):apiClient.post<PayrollRecord>(`/payroll/${id}/approve`);}
export async function validatePayrollMonth(month:string):Promise<PayrollValidationIssue[]>{return USE_MOCKS?mockDelay(payrollValidationIssues,500):list<PayrollValidationIssue>(await apiClient.post<any>("/payroll/validate",{payrollMonth:month}));}
