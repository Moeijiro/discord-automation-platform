import { useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { api } from "@/lib/api";
import type { ModeInfo, User } from "@/lib/types";
import { AuthContext, type AuthValue } from "@/context/auth-context";

/**
 * Resolves the session once, at boot. Everything downstream can then treat
 * `user` as settled: null means "not signed in", not "not loaded yet".
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [mode, setMode] = useState<ModeInfo | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setMode(await api.mode().catch(() => null));
    // A 401 here is the normal "not signed in" case, not an error to surface.
    setUser(await api.me().catch(() => null));
    setLoading(false);
  }, []);

  // The session lives on the server, not in React state: fetching it on mount
  // is exactly the "synchronise with an external system" case effects are for.
  useEffect(() => {
    // oxlint-disable-next-line react/set-state-in-effect
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
