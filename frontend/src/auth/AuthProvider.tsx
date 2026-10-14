import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { apiClient } from "../api/client";

interface AuthContextValue {
  isAuthenticated: boolean;
  isSigningIn: boolean;
  signIn: (username: string, password: string) => Promise<void>;
  signOut: () => Promise<boolean>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(apiClient.hasSession());
  const [isSigningIn, setIsSigningIn] = useState(false);

  useEffect(() => {
    apiClient.setSessionExpiredHandler(() => setIsAuthenticated(false));
    return () => apiClient.setSessionExpiredHandler(null);
  }, []);

  const signIn = useCallback(async (username: string, password: string) => {
    setIsSigningIn(true);
    try {
      apiClient.setTokens(await apiClient.login(username, password));
      setIsAuthenticated(true);
    } finally {
      setIsSigningIn(false);
    }
  }, []);

  const signOut = useCallback(async () => {
    const revocationConfirmed = await apiClient.logout();
    setIsAuthenticated(false);
    return revocationConfirmed;
  }, []);

  const value = useMemo(
    () => ({ isAuthenticated, isSigningIn, signIn, signOut }),
    [isAuthenticated, isSigningIn, signIn, signOut],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider.");
  return context;
}
