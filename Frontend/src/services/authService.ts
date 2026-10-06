// FastAPI integration:
// POST /auth/login -> { access_token, token_type, user }
// POST /auth/register -> AppUser
// POST /auth/refresh -> { access_token }
// POST /auth/logout -> 204
// GET /auth/me -> AppUser
import { appUsers } from "@/data/mockData";
import { listUsers, verifyUserPassword } from "./userService";
import { apiClient, AUTH_LOGIN_MODE, mockDelay, USE_MOCKS } from "./api";
import type { AppUser } from "@/types";

export interface LoginPayload { username: string; password: string; rememberMe: boolean; }
export interface LoginResult { accessToken: string; user: AppUser; }

export const DEMO_ACCOUNTS: { username: string; role: string }[] = appUsers.map((u) => ({ username: u.username, role: u.role }));

function normalizeUser(raw: any): AppUser {
  const firstName = raw.firstName ?? raw.first_name ?? raw.name?.split(" ")[0] ?? "User";
  const lastName = raw.lastName ?? raw.last_name ?? raw.name?.split(" ").slice(1).join(" ") ?? "";
  const role = raw.role ?? raw.roles?.[0] ?? "Employee";
  return {
    id: String(raw.id ?? raw.user_id ?? raw.userId),
    username: raw.username ?? raw.email ?? "",
    firstName,
    lastName,
    email: raw.email ?? "",
    phone: raw.phone ?? raw.phone_number ?? "",
    employeeId: raw.employeeId ?? raw.employee_id ?? null,
    role,
    status: raw.status ?? "Active",
    avatarColor: raw.avatarColor ?? raw.avatar_color ?? "bg-blue-500",
  } as AppUser;
}

function normalizeLoginResponse(raw: any): LoginResult {
  const token = raw.accessToken ?? raw.access_token ?? raw.token;
  const user = raw.user ?? raw.data?.user ?? raw;
  if (!token) throw new Error("The login response did not contain an access token.");
  return { accessToken: token, user: normalizeUser(user) };
}

export async function login(payload: LoginPayload): Promise<LoginResult> {
  if (!USE_MOCKS) {
    const raw = AUTH_LOGIN_MODE === "form"
      ? await apiClient.postForm<any>("/auth/login", { username: payload.username.trim(), password: payload.password })
      : await apiClient.post<any>("/auth/login", { username: payload.username.trim(), password: payload.password });
    return normalizeLoginResponse(raw);
  }

  const users = await listUsers();
  const user = users.find((u) => u.username.toLowerCase() === payload.username.trim().toLowerCase())
    ?? appUsers.find((u) => u.username.toLowerCase() === payload.username.trim().toLowerCase());
  if (!user || !payload.password || payload.password.length < 4 || !verifyUserPassword(user.id, payload.password)) {
    await mockDelay(null, 450);
    throw new Error("Invalid username or password.");
  }
  if (user.status !== "Active") throw new Error("This account has been deactivated. Contact your System Administrator.");
  return mockDelay({ accessToken: `mock.${user.id}.${Date.now()}`, user }, 450);
}

export async function fetchCurrentUser(): Promise<AppUser | undefined> {
  if (!USE_MOCKS) return normalizeUser(await apiClient.get<any>("/auth/me"));
  return mockDelay(appUsers[0]);
}

export async function registerUser(payload: Record<string, unknown>): Promise<AppUser> {
  if (!USE_MOCKS) return normalizeUser(await apiClient.post<any>("/auth/register", payload));
  return normalizeUser(payload);
}

export async function logout(): Promise<void> {
  if (!USE_MOCKS) {
    await apiClient.post<void>("/auth/logout").catch((err) => {
      // A logout endpoint may legitimately be absent while the token is still local.
      if (err?.status !== 404) throw err;
    });
  }
}
