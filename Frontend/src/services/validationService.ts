// FastAPI: GET /payroll-validation
import { payrollValidationIssues } from "@/data/mockData"; import { createMockStore } from "./mockStore"; import { apiClient, USE_MOCKS } from "./api"; import type { PayrollValidationIssue } from "@/types";
const store=createMockStore<PayrollValidationIssue>(payrollValidationIssues); const list=<T,>(r:any):T[]=>Array.isArray(r)?r:r?.items??r?.data??r?.results??[];
export const listValidationIssues=async():Promise<PayrollValidationIssue[]>=>USE_MOCKS?store.list():list<PayrollValidationIssue>(await apiClient.get<any>("/payroll-validation"));
export const resolveValidationIssue=async(id:string)=>USE_MOCKS?store.update(id,{status:"Resolved"}):apiClient.put<PayrollValidationIssue>(`/payroll-validation/${id}`,{status:"Resolved"});
