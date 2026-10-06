// FastAPI: GET/POST /backups, POST /backups/{id}/restore
import { backups } from "@/data/mockData"; import { createMockStore } from "./mockStore"; import { apiClient, USE_MOCKS } from "./api"; import type { Backup } from "@/types";
const store=createMockStore<Backup>(backups); const list=<T,>(r:any):T[]=>Array.isArray(r)?r:r?.items??r?.data??r?.results??[];
export const listBackups=async():Promise<Backup[]>=>USE_MOCKS?store.list():list<Backup>(await apiClient.get<any>("/backups"));
export async function createBackup(type:Backup["type"],createdBy:string){if(USE_MOCKS){const b:Backup={id:`BKP-${Date.now()}`,type,timestamp:new Date().toISOString(),size:type==="Full"?"1.9 GB":type==="Incremental"?"298 MB":"512 MB",location:`manual://${Date.now()}`,createdBy,status:"Completed",restoreStatus:"N/A",checksum:Math.random().toString(16).slice(2,10),remarks:"Manually triggered backup."};return store.create(b);}return apiClient.post<Backup>("/backups",{type,createdBy});}
export async function restoreBackup(id:string){return USE_MOCKS?store.update(id,{restoreStatus:"Restored"}):apiClient.post<Backup>(`/backups/${id}/restore`);}
