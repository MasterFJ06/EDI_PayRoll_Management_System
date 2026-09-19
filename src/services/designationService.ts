// FastAPI: GET/POST /designations, GET/PUT/DELETE /designations/{id}
import { designations } from "@/data/mockData"; import { createMockStore } from "./mockStore"; import { apiClient, USE_MOCKS } from "./api"; import type { Designation } from "@/types";
const store=createMockStore<Designation>(designations); const list=<T,>(r:any):T[]=>Array.isArray(r)?r:r?.items??r?.data??r?.results??[];
export const listDesignations=async():Promise<Designation[]>=>USE_MOCKS?store.list():list<Designation>(await apiClient.get<any>("/designations"));
export const getDesignation=async(id:string)=>USE_MOCKS?store.get(id):apiClient.get<Designation>(`/designations/${id}`);
export const createDesignation=async(x:Designation)=>USE_MOCKS?store.create(x):apiClient.post<Designation>("/designations",x);
export const updateDesignation=async(id:string,p:Partial<Designation>)=>USE_MOCKS?store.update(id,p):apiClient.put<Designation>(`/designations/${id}`,p);
export async function deleteDesignation(id:string){if(USE_MOCKS)return store.remove(id);await apiClient.delete(`/designations/${id}`);}
