"use client";

import { usePathname, useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import type { CurrentUser } from "@/lib/types";

type AuthContextValue = {
  user: CurrentUser | null;
  ready: boolean;
  setUser: (user: CurrentUser | null) => void;
  refresh: () => Promise<CurrentUser | null>;
};

const AuthContext = createContext<AuthContextValue>({
  user: null,
  ready: false,
  setUser: () => undefined,
  refresh: async () => null,
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [ready, setReady] = useState(false);
  const pathname = usePathname();
  const router = useRouter();
  const isLogin = pathname === "/login";

  const refresh = useCallback(async () => {
    try {
      const current = await api<CurrentUser>("/api/auth/me");
      setUser(current);
      return current;
    } catch {
      setUser(null);
      return null;
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const current = await refresh();
      if (cancelled) return;
      setReady(true);
      if (!current && !isLogin) {
        router.replace("/login");
      }
      if (current && isLogin) {
        router.replace("/dashboard");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [isLogin, refresh, router]);

  const value = useMemo(() => ({ user, ready, setUser, refresh }), [user, ready, refresh]);

  if (!isLogin && !ready) {
    return <div className="main">Loading workspace…</div>;
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}

export function useUser() {
  return useContext(AuthContext).user;
}

export function can(user: CurrentUser | null, permission: string) {
  return Boolean(user?.permissions.includes(permission));
}
