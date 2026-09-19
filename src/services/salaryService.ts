// FastAPI: GET/POST /salary-structures, GET/PUT /salary-structures/{id}
import { salaryStructures } from "@/data/mockData"; import { createMockStore } from "./mockStore"; import { apiClient, USE_MOCKS } from "./api"; import type { SalaryStructure } from "@/types";
const store=createMockStore<SalaryStructure>(salaryStructures); const list=<T,>(r:any):T[]=>Array.isArray(r)?r:r?.items??r?.data??r?.results??[];
export const listSalaryStructures=async():Promise<SalaryStructure[]>=>USE_MOCKS?store.list():list<SalaryStructure>(await apiClient.get<any>("/salary-structures"));
export const getSalaryStructure=async(id:string)=>USE_MOCKS?store.get(id):apiClient.get<SalaryStructure>(`/salary-structures/${id}`);
export const createSalaryStructure=async(x:SalaryStructure)=>USE_MOCKS?store.create(x):apiClient.post<SalaryStructure>("/salary-structures",x);
export const updateSalaryStructure=async(id:string,p:Partial<SalaryStructure>)=>USE_MOCKS?store.update(id,p):apiClient.put<SalaryStructure>(`/salary-structures/${id}`,p);
export function computeGross(s:Pick<SalaryStructure,"basic"|"hra"|"da"|"specialAllowance"|"travelAllowance"|"medicalAllowance"|"otherAllowances"|"bonus"|"overtimeRate">){return s.basic+s.hra+s.da+s.specialAllowance+s.travelAllowance+s.medicalAllowance+s.otherAllowances+s.bonus;}
export function computeDeductions(s:Pick<SalaryStructure,"providentFund"|"esi"|"professionalTax"|"incomeTax"|"insurance"|"loanDeduction"|"otherDeductions">){return s.providentFund+s.esi+s.professionalTax+s.incomeTax+s.insurance+s.loanDeduction+s.otherDeductions;}
