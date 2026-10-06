// FastAPI: GET/POST /departments, GET/PUT/DELETE /departments/{id}
import { departments } from "@/data/mockData"; import { createMockStore } from "./mockStore"; import { apiClient, USE_MOCKS } from "./api"; import type { Department } from "@/types";
const store=createMockStore<Department>(departments); const list=<T,>(r:any):T[]=>Array.isArray(r)?r:r?.items??r?.data??r?.results??[];
export const listDepartments=async():Promise<Department[]>=>USE_MOCKS?store.list():list<Department>(await apiClient.get<any>("/departments"));
export const getDepartment=async(id:string)=>USE_MOCKS?store.get(id):apiClient.get<Department>(`/departments/${id}`);
export const createDepartment=async(x:Department)=>USE_MOCKS?store.create(x):apiClient.post<Department>("/departments",x);
export const updateDepartment=async(id:string,p:Partial<Department>)=>USE_MOCKS?store.update(id,p):apiClient.put<Department>(`/departments/${id}`,p);
export async function deleteDepartment(id:string){if(USE_MOCKS)return store.remove(id);await apiClient.delete(`/departments/${id}`);}
