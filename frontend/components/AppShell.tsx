"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createContext, useContext, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { CurrentUser } from "@/lib/types";

const UserContext = createContext<CurrentUser | null>(null);

export function AppShell({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [error, setError] = useState("");
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    api<CurrentUser>("/api/auth/me")
      .then(setUser)
      .catch(() => router.replace("/login"));
  }, [router]);

  async function logout() {
    await api("/api/auth/logout", { method: "POST" });
    router.replace("/login");
  }

  if (!user && !error) {
    return <div className="main">Loading workspace…</div>;
  }
  if (!user) {
    return <div className="main">{error}</div>;
  }

  return (
    <UserContext.Provider value={user}>
      <div className="app-shell">
        <aside className="sidebar">
          <div>
            <div className="brand-kicker">RMH HCTM UKM</div>
            <strong>Operations Platform</strong>
            <div className="muted" style={{ color: "rgba(255,255,255,0.7)", marginTop: 8 }}>
              {user.name}
              <br />
              {user.role.replaceAll("_", " ")}
            </div>
          </div>
          <nav aria-label="Primary">
            {user.navigation.map((item) => (
              <Link key={item.href} href={item.href} className={pathname.startsWith(item.href) ? "active" : ""}>
                {item.label}
              </Link>
            ))}
          </nav>
          <button className="linkish" onClick={logout}>
            Sign out
          </button>
        </aside>
        <div className="main">{children}</div>
      </div>
    </UserContext.Provider>
  );
}

export function useUser() {
  return useContext(UserContext);
}

export function can(user: CurrentUser | null, permission: string) {
  return Boolean(user?.permissions.includes(permission));
}
