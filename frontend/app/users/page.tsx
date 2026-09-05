"use client";

import { FormEvent, useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { Banner, Field, Modal, PageHeader } from "@/components/ui";
import { api, HttpError } from "@/lib/api";

type UserRow = { id: number; name: string; email: string; role: string; active: boolean };

const ROLES = [
  ["admin", "Operations Manager / Admin"],
  ["duty_officer", "Duty Officer / Front Desk"],
  ["social_worker", "Admissions / Social Worker"],
  ["finance", "Finance / Donations Officer"],
  ["viewer", "Read-only / Reporting Viewer"],
];

export default function UsersPage() {
  const [rows, setRows] = useState<UserRow[]>([]);
  const [error, setError] = useState("");
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", password: "", role: "duty_officer", active: true });

  async function load() {
    setRows(await api<UserRow[]>("/api/users"));
  }

  useEffect(() => {
    load().catch((err) => setError(err.message));
  }, []);

  async function create(event: FormEvent) {
    event.preventDefault();
    try {
      await api("/api/users", { method: "POST", body: JSON.stringify(form) });
      setOpen(false);
      await load();
    } catch (err) {
      setError(err instanceof HttpError ? err.message : "Unable to create user");
    }
  }

  return (
    <AppShell>
      <PageHeader title="Users" subtitle="Role changes take effect on the next request. Passwords are never shown in audit logs." actions={<button className="btn" onClick={() => setOpen(true)}>Add user</button>} />
      {error ? <Banner kind="error">{error}</Banner> : null}
      <div className="card table-wrap">
        <table>
          <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th><th></th></tr></thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id}>
                <td>{row.name}</td>
                <td>{row.email}</td>
                <td>{row.role.replace("_", " ")}</td>
                <td>{row.active ? "Active" : "Inactive"}</td>
                <td>
                  <button
                    className="btn secondary"
                    onClick={async () => {
                      const action = row.active ? "Deactivate" : "Activate";
                      if (!window.confirm(`${action} ${row.email}?`)) return;
                      await api(`/api/users/${row.id}`, { method: "PATCH", body: JSON.stringify({ active: !row.active }) });
                      await load();
                    }}
                  >
                    {row.active ? "Deactivate" : "Activate"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {open ? (
        <Modal title="New user" onClose={() => setOpen(false)}>
          <form className="form-grid" onSubmit={create}>
            <Field label="Name"><input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
            <Field label="Email"><input type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></Field>
            <Field label="Password"><input type="password" required minLength={10} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></Field>
            <Field label="Role">
              <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
                {ROLES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </Field>
            <button className="btn">Create</button>
          </form>
        </Modal>
      ) : null}
    </AppShell>
  );
}
