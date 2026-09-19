// FastAPI: GET /deductions, GET /tax-rules
import { deductions } from "@/data/mockData"; import { apiClient, mockDelay, USE_MOCKS } from "./api"; import type { Deduction } from "@/types";
const list=<T,>(r:any):T[]=>Array.isArray(r)?r:r?.items??r?.data??r?.results??[];
export async function listDeductions():Promise<Deduction[]> { return USE_MOCKS?mockDelay(deductions):list<Deduction>(await apiClient.get<any>("/deductions")); }
