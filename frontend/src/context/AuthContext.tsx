import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { api, ApiError } from "@/lib/api";
import type { ModeInfo, User } from "@/lib/types";

interface AuthValue {
  user: User | null;
  mode: ModeInfo | null;
  loading: boolean;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthValue | null>(null);

/**
 * Resolves the session once, at boot. Everything downstream can then treat
 * `user` as settled: null means "not signed in", not "not loaded yet".
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [mode, setMode] = useState<ModeInfo | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    const [modeInfo] = await Promise.all([api.mode().catch(() => null)]);
    setMode(modeInfo);
    try {
      setUser(await api.me());
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) setUser(null);
      else setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const value = useMemo<AuthValue>(
    () => ({
      user,
      mode,
      loading,
      logout: async () => {
        await api.logout().catch(() => undefined);
        setUser(null);
      },
      refresh: async () => {
        setLoading(true);
        await load();
      },
    }),
    [user, mode, loading, load],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside <AuthProvider>");
  return value;
}
