"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Banner } from "@/components/ui";
import { can, useAuth, useUser } from "@/components/AuthProvider";

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, setUser } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  async function logout() {
    await api("/api/auth/logout", { method: "POST" });
    setUser(null);
    router.replace("/login");
  }

  if (!user) {
    return <div className="main">Loading workspace…</div>;
  }

  const allowed = user.navigation.some((item) => pathname === item.href || pathname.startsWith(`${item.href}/`));

  return (
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
        <button className="linkish" onClick={logout} type="button">
          Sign out
        </button>
      </aside>
      <div className="main">
        {allowed ? children : <Banner kind="error">You do not have permission to open this page.</Banner>}
      </div>
    </div>
  );
}

export { can, useAuth, useUser };
