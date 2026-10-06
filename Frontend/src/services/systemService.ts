// FastAPI: GET /monitoring
import { systemMonitors } from "@/data/mockData"; import { apiClient, mockDelay, USE_MOCKS } from "./api"; import type { SystemMonitor } from "@/types";
const list=<T,>(r:any):T[]=>Array.isArray(r)?r:r?.items??r?.data??r?.results??[];
export async function listSystemMonitors():Promise<SystemMonitor[]> { return USE_MOCKS?mockDelay(systemMonitors):list<SystemMonitor>(await apiClient.get<any>("/monitoring")); }
