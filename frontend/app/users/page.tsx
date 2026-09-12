"use client";

import { FormEvent, useEffect, useState } from "react";
import { AppShell, can, useUser } from "@/components/AppShell";
import { Banner, Empty, Field, Loading, Modal, PageHeader } from "@/components/ui";
import { api, formatError } from "@/lib/api";

type UserRow = { id: number; name: string; email: string; role: string; active: boolean };

const ROLES = [
  ["admin", "Operations Manager / Admin"],
  ["duty_officer", "Duty Officer / Front Desk"],
  ["social_worker", "Admissions / Social Worker"],
  ["finance", "Finance / Donations Officer"],
  ["viewer", "Read-only / Reporting Viewer"],
];

export default function UsersPage() {
  const user = useUser();
  const canManage = can(user, "users:manage");
  const [rows, setRows] = useState<UserRow[] | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<UserRow | null>(null);
  const [password, setPassword] = useState("");
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
      setSuccess("User created.");
      await load();
    } catch (err) {
      setError(formatError(err, "Unable to create user"));
    }
  }

  async function saveRole(event: FormEvent) {
    event.preventDefault();
    if (!editing) return;
    try {
      const body: { role: string; password?: string } = { role: editing.role };
      if (password) body.password = password;
      await api(`/api/users/${editing.id}`, { method: "PATCH", body: JSON.stringify(body) });
      setEditing(null);
      setPassword("");
      setSuccess("User updated.");
      await load();
    } catch (err) {
      setError(formatError(err, "Unable to update user"));
    }
  }

  return (
    <AppShell>
      <PageHeader
        title="Users"
        subtitle="Role changes take effect on the next request. Passwords are never shown in audit logs."
        actions={canManage ? <button className="btn" onClick={() => setOpen(true)}>Add user</button> : null}
      />
      {error ? <Banner kind="error">{error}</Banner> : null}
      {success ? <Banner kind="success">{success}</Banner> : null}
      <div className="card table-wrap">
        {!rows ? <Loading>Loading users…</Loading> : !rows.length ? <Empty>No users found.</Empty> : (
          <table>
            <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th><th></th></tr></thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id}>
                  <td>{row.name}</td>
                  <td>{row.email}</td>
                  <td>{row.role.replaceAll("_", " ")}</td>
                  <td>{row.active ? "Active" : "Inactive"}</td>
                  <td>
                    {canManage ? (
                      <>
                        <button className="btn secondary" type="button" onClick={() => { setEditing(row); setPassword(""); }}>
                          Edit role
                        </button>
                        <button
                          className="btn secondary"
                          style={{ marginLeft: 8 }}
                          onClick={async () => {
                            const action = row.active ? "Deactivate" : "Activate";
                            if (!window.confirm(`${action} ${row.email}?`)) return;
                            try {
                              await api(`/api/users/${row.id}`, { method: "PATCH", body: JSON.stringify({ active: !row.active }) });
                              setSuccess(`${action}d ${row.email}.`);
                              await load();
                            } catch (err) {
                              setError(formatError(err, "Unable to update user"));
                            }
                          }}
                        >
                          {row.active ? "Deactivate" : "Activate"}
                        </button>
                      </>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      {open && canManage ? (
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
      {editing && canManage ? (
        <Modal title={`Edit user · ${editing.email}`} onClose={() => setEditing(null)}>
          <form className="form-grid" onSubmit={saveRole}>
            <Field label="Role">
              <select value={editing.role} onChange={(e) => setEditing({ ...editing, role: e.target.value })}>
                {ROLES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </Field>
            <Field label="New password" hint="Leave blank to keep the current password.">
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" />
            </Field>
            <button className="btn">Save</button>
          </form>
        </Modal>
      ) : null}
    </AppShell>
  );
}
