import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { fetchCurrentUser, login as loginRequest, logout as logoutRequest, type LoginPayload } from "@/services/authService";
import { hasPermission } from "@/config/permissions";
import type { AppUser, Permission, Role } from "@/types";
import { appUsers } from "@/data/mockData";

interface AuthContextValue {
  user: AppUser | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  sessionExpired: boolean;
  login: (payload: LoginPayload) => Promise<void>;
  logout: () => Promise<void>;
  switchDemoRole: (role: Role) => void;
  can: (permission: Permission) => boolean;
  dismissSessionExpired: () => void;
}
const AuthContext = createContext<AuthContextValue | undefined>(undefined);
const TOKEN_KEY = "epms_access_token";
const USER_KEY = "epms_user";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AppUser | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [sessionExpired, setSessionExpired] = useState(false);

  useEffect(() => {
    let active = true;
    (async () => {
      const token = localStorage.getItem(TOKEN_KEY) ?? sessionStorage.getItem(TOKEN_KEY);
      if (!token) { if (active) setIsLoading(false); return; }
      try {
        const currentUser = await fetchCurrentUser();
        if (!active) return;
        if (currentUser) {
          setAccessToken(token);
          setUser(currentUser);
          const storage = localStorage.getItem(TOKEN_KEY) ? localStorage : sessionStorage;
          storage.setItem(USER_KEY, JSON.stringify(currentUser));
        }
      } catch {
        localStorage.removeItem(TOKEN_KEY); sessionStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY); sessionStorage.removeItem(USER_KEY);
      } finally { if (active) setIsLoading(false); }
    })();
    return () => { active = false; };
  }, []);

  useEffect(() => {
    const handler = () => {
      setSessionExpired(true); setUser(null); setAccessToken(null);
      localStorage.removeItem(TOKEN_KEY); sessionStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY); sessionStorage.removeItem(USER_KEY);
    };
    window.addEventListener("epms:session-expired", handler);
    return () => window.removeEventListener("epms:session-expired", handler);
  }, []);

  const login = useCallback(async (payload: LoginPayload) => {
    const result = await loginRequest(payload);
    const storage = payload.rememberMe ? localStorage : sessionStorage;
    const other = payload.rememberMe ? sessionStorage : localStorage;
    other.removeItem(TOKEN_KEY); other.removeItem(USER_KEY);
    storage.setItem(TOKEN_KEY, result.accessToken);
    storage.setItem(USER_KEY, JSON.stringify(result.user));
    setUser(result.user); setAccessToken(result.accessToken); setSessionExpired(false);
  }, []);

  const logout = useCallback(async () => {
    try { await logoutRequest(); } finally {
      setUser(null); setAccessToken(null);
      localStorage.removeItem(TOKEN_KEY); localStorage.removeItem(USER_KEY);
      sessionStorage.removeItem(TOKEN_KEY); sessionStorage.removeItem(USER_KEY);
    }
  }, []);

  const switchDemoRole = useCallback((role: Role) => {
    const target = appUsers.find((candidate) => candidate.role === role);
    if (!target) return;
    const demoToken = `mock.${target.id}.role.${Date.now()}`;
    setUser(target); setAccessToken(demoToken);
    localStorage.setItem(TOKEN_KEY, demoToken); localStorage.setItem(USER_KEY, JSON.stringify(target));
    sessionStorage.removeItem(TOKEN_KEY); sessionStorage.removeItem(USER_KEY); setSessionExpired(false);
  }, []);

  const can = useCallback((permission: Permission) => hasPermission(user?.role, permission), [user]);
  const value = useMemo(() => ({ user, accessToken, isAuthenticated: Boolean(user && accessToken), isLoading, sessionExpired, login, logout, switchDemoRole, can, dismissSessionExpired: () => setSessionExpired(false) }), [user, accessToken, isLoading, sessionExpired, login, logout, switchDemoRole, can]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
export function useAuth() { const ctx = useContext(AuthContext); if (!ctx) throw new Error("useAuth must be used within AuthProvider"); return ctx; }
