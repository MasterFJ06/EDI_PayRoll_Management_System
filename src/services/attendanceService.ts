// FastAPI: GET/POST /attendance, PUT /attendance/{id}
import { attendanceRecords } from "@/data/mockData"; import { createMockStore } from "./mockStore"; import { apiClient, USE_MOCKS } from "./api"; import type { AttendanceRecord } from "@/types";
const store=createMockStore<AttendanceRecord>(attendanceRecords); const list=<T,>(r:any):T[]=>Array.isArray(r)?r:r?.items??r?.data??r?.results??[];
export const listAttendance=async():Promise<AttendanceRecord[]>=>USE_MOCKS?store.list():list<AttendanceRecord>(await apiClient.get<any>("/attendance"));
export const getAttendance=async(id:string)=>USE_MOCKS?store.get(id):apiClient.get<AttendanceRecord>(`/attendance/${id}`);
export const createAttendance=async(x:AttendanceRecord)=>USE_MOCKS?store.create(x):apiClient.post<AttendanceRecord>("/attendance",x);
export const updateAttendance=async(id:string,p:Partial<AttendanceRecord>)=>USE_MOCKS?store.update(id,p):apiClient.put<AttendanceRecord>(`/attendance/${id}`,p);
