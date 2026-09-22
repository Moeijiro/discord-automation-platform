import { createContext, useContext } from "react";
import type { ModeInfo, User } from "@/lib/types";

export interface AuthValue {
  user: User | null;
  mode: ModeInfo | null;
  loading: boolean;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

/** Split from the provider component so the module exports no mixed concerns. */
export const AuthContext = createContext<AuthValue | null>(null);

export function useAuth(): AuthValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside <AuthProvider>");
  return value;
}
