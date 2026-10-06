// FastAPI: GET/POST /users, GET/PUT/DELETE /users/{id}, GET/POST/PUT /roles
import { appUsers } from "@/data/mockData";
import { createMockStore } from "./mockStore";
import { apiClient, USE_MOCKS } from "./api";
import type { AppUser } from "@/types";
const store = createMockStore<AppUser>(appUsers, "users");
const normalize = (raw: any): AppUser => ({ id:String(raw.id ?? raw.user_id), username:raw.username ?? raw.email ?? "", firstName:raw.firstName ?? raw.first_name ?? "", lastName:raw.lastName ?? raw.last_name ?? "", email:raw.email ?? "", phone:raw.phone ?? raw.phone_number ?? "", employeeId:raw.employeeId ?? raw.employee_id ?? null, role:raw.role ?? "Employee", status:raw.status ?? "Active", avatarColor:raw.avatarColor ?? raw.avatar_color ?? "bg-blue-500" });
const unwrap = <T>(raw: any): T[] => Array.isArray(raw) ? raw : raw?.items ?? raw?.data ?? raw?.results ?? [];
export async function listUsers(): Promise<AppUser[]> { return USE_MOCKS ? store.list() : (unwrap<any>(await apiClient.get<any>("/users")).map(normalize)); }
export async function getUser(id:string): Promise<AppUser|undefined> { return USE_MOCKS ? store.get(id) : normalize(await apiClient.get<any>(`/users/${id}`)); }
export async function createUser(item: AppUser): Promise<AppUser> { return USE_MOCKS ? store.create(item) : normalize(await apiClient.post<any>("/users", item)); }
export async function updateUser(id:string, patch:Partial<AppUser>): Promise<AppUser|undefined> { return USE_MOCKS ? store.update(id,patch) : normalize(await apiClient.put<any>(`/users/${id}`,patch)); }
export async function deleteUser(id:string): Promise<void> { if (USE_MOCKS) return store.remove(id); await apiClient.delete(`/users/${id}`); }
const PASSWORD_KEY = "epms_user_passwords";
function readPasswords(): Record<string,string> { try { return JSON.parse(localStorage.getItem(PASSWORD_KEY) ?? "{}"); } catch { return {}; } }
export function setUserPassword(userId:string,password:string) { const p=readPasswords(); p[userId]=password; localStorage.setItem(PASSWORD_KEY,JSON.stringify(p)); }
export function verifyUserPassword(userId:string,password:string) { const p=readPasswords(); return p[userId] ? p[userId]===password : password.length>=4; }
