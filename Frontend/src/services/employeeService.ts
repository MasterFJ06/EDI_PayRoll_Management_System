// FastAPI: GET/POST /employees, GET/PUT/DELETE /employees/{id}
import { employees } from "@/data/mockData";
import { createMockStore } from "./mockStore";
import { apiClient, USE_MOCKS } from "./api";
import type { Employee } from "@/types";
const store=createMockStore<Employee>(employees);
const list = <T,>(raw:any):T[] => Array.isArray(raw) ? raw : raw?.items ?? raw?.data ?? raw?.results ?? [];
export const listEmployees = async():Promise<Employee[]> => USE_MOCKS ? store.list() : list<Employee>(await apiClient.get<any>("/employees"));
export const getEmployee = async(id:string):Promise<Employee|undefined> => USE_MOCKS ? store.get(id) : await apiClient.get<Employee>(`/employees/${id}`);
export const createEmployee = async(item:Employee):Promise<Employee> => USE_MOCKS ? store.create(item) : await apiClient.post<Employee>("/employees",item);
export const updateEmployee = async(id:string,patch:Partial<Employee>):Promise<Employee|undefined> => USE_MOCKS ? store.update(id,patch) : await apiClient.put<Employee>(`/employees/${id}`,patch);
export const deleteEmployee = async(id:string):Promise<void> => USE_MOCKS ? store.remove(id) : void await apiClient.delete(`/employees/${id}`);
