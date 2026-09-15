"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { api, formatError } from "@/lib/api";
import { Banner, Field, Modal } from "@/components/ui";
import { can, useAuth, useUser } from "@/components/AuthProvider";

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, setUser } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const [navOpen, setNavOpen] = useState(false);
  const [passwordOpen, setPasswordOpen] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [passwordSuccess, setPasswordSuccess] = useState("");
  const [savingPassword, setSavingPassword] = useState(false);

  async function logout() {
    await api("/api/auth/logout", { method: "POST" });
    setUser(null);
    router.replace("/login");
  }

  async function changePassword(event: FormEvent) {
    event.preventDefault();
    setSavingPassword(true);
    setPasswordError("");
    try {
      await api("/api/auth/change-password", {
        method: "POST",
        body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
      });
      setPasswordSuccess("Password updated.");
      setPasswordOpen(false);
      setCurrentPassword("");
      setNewPassword("");
    } catch (err) {
      setPasswordError(formatError(err, "Unable to update password"));
    } finally {
      setSavingPassword(false);
    }
  }

  if (!user) {
    return <div className="main">Loading workspace…</div>;
  }

  const allowed = user.navigation.some((item) => pathname === item.href || pathname.startsWith(`${item.href}/`));

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="brand-kicker">RMH HCTM UKM</div>
          <strong>Operations Platform</strong>
          <div className="muted" style={{ color: "rgba(255,255,255,0.7)", marginTop: 8 }}>
            {user.name}
            <br />
            {user.role.replaceAll("_", " ")}
          </div>
          <button
            className="nav-toggle"
            type="button"
            aria-expanded={navOpen}
            aria-controls="primary-nav"
            onClick={() => setNavOpen((open) => !open)}
          >
            {navOpen ? "Close menu" : "Menu"}
          </button>
        </div>
        <nav id="primary-nav" aria-label="Primary" className={navOpen ? "open" : ""}>
          {user.navigation.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={pathname.startsWith(item.href) ? "active" : ""}
              onClick={() => setNavOpen(false)}
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <div>
          <button className="linkish" onClick={() => { setPasswordOpen(true); setPasswordError(""); }} type="button">
            Change password
          </button>
          <button className="linkish" onClick={logout} type="button">
            Sign out
          </button>
        </div>
      </aside>
      <div className="main">
        {passwordSuccess ? <Banner kind="success">{passwordSuccess}</Banner> : null}
        {allowed ? children : <Banner kind="error">You do not have permission to open this page.</Banner>}
      </div>
      {passwordOpen ? (
        <Modal title="Change password" onClose={() => setPasswordOpen(false)}>
          {passwordError ? <Banner kind="error">{passwordError}</Banner> : null}
          <form className="form-grid" onSubmit={changePassword}>
            <Field label="Current password">
              <input type="password" required autoComplete="current-password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} />
            </Field>
            <Field label="New password" hint="At least 10 characters. Never written to the audit log.">
              <input type="password" required minLength={10} autoComplete="new-password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
            </Field>
            <button className="btn" disabled={savingPassword}>{savingPassword ? "Updating…" : "Update password"}</button>
          </form>
        </Modal>
      ) : null}
    </div>
  );
}

export { can, useAuth, useUser };
