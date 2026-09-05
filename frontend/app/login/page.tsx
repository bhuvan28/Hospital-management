"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { api, HttpError } from "@/lib/api";
import type { CurrentUser } from "@/lib/types";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api<{ user: CurrentUser }>("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof HttpError ? err.message : "Unable to sign in");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-shell">
      <form className="login-card" onSubmit={onSubmit}>
        <div className="brand-kicker">Ronald McDonald House</div>
        <h1>RMH HCTM UKM</h1>
        <p className="muted">Operations platform for family stay, occupancy, donations and reporting.</p>
        {error ? <div className="banner error">{error}</div> : null}
        <div className="form-grid" style={{ gridTemplateColumns: "1fr" }}>
          <div>
            <label htmlFor="email">Email</label>
            <input id="email" type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>
          <div>
            <label htmlFor="password">Password</label>
            <input id="password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </div>
        </div>
        <button className="btn" style={{ marginTop: 16, width: "100%" }} disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
        <p className="muted" style={{ marginTop: 18, fontSize: "0.85rem" }}>
          Development seed accounts are listed in the README and are for local use only.
        </p>
      </form>
    </div>
  );
}
