// FastAPI: GET /audit-logs
import { auditLogs } from "@/data/mockData"; import { apiClient, mockDelay, USE_MOCKS } from "./api"; import type { AuditLog } from "@/types";
const list=<T,>(r:any):T[]=>Array.isArray(r)?r:r?.items??r?.data??r?.results??[];
export async function listAuditLogs():Promise<AuditLog[]> { return USE_MOCKS?mockDelay(auditLogs):list<AuditLog>(await apiClient.get<any>("/audit-logs")); }
