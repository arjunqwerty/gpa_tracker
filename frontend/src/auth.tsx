// Who is logged in. Wrap the app in <AuthProvider>; read or change the account with useAuth().
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, renewSession, session } from "./api";
import type { Account } from "./types";

interface AuthState {
  account: Account | null | undefined; // undefined while checking, null when logged out
  setAccount: (account: Account | null) => void;
}

const AuthContext = createContext<AuthState>({ account: undefined, setAccount: () => {} });

export function AuthProvider({ children }: { children: ReactNode }) {
  const [account, setAccount] = useState<Account | null>();

  useEffect(() => {
    session.onEnded = () => setAccount(null);
    api.get<Account>("/api/auth/me").then(setAccount, () => setAccount(null));
  }, []);

  // Renew the 15-minute access cookie in the background, so plain download links keep working.
  useEffect(() => {
    if (!account) return;
    const timer = setInterval(renewSession, 10 * 60 * 1000);
    return () => clearInterval(timer);
  }, [account]);

  return <AuthContext.Provider value={{ account, setAccount }}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);
