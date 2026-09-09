"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { AppShell, can, useUser } from "@/components/AppShell";
import { Banner, ConfirmButton, Empty, Field, Loading, Modal, PageHeader } from "@/components/ui";
import { api, formatError } from "@/lib/api";

type Entry = {
  id: number;
  month: string;
  budgeted: string;
  actual: string;
  groceries_sponsored: string;
  category: string;
  remarks: string | null;
  balance: string;
};

const CATEGORIES = [
  ["groceries", "Groceries"],
  ["stationery_office", "Stationery & Office"],
  ["kitchen_laundry", "Kitchen & Laundry Equipment"],
  ["other", "Other"],
  ["maintenance_repair", "Maintenance & Repair"],
];

export default function PettyCashPage() {
  const user = useUser();
  const canWrite = can(user, "petty_cash:write");
  const [rows, setRows] = useState<Entry[] | null>(null);
  const [summary, setSummary] = useState<{ total_budgeted: string; total_actual: string; total_balance: string } | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [open, setOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [year, setYear] = useState(String(new Date().getFullYear()));
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({
    month: "",
    budgeted: "",
    actual: "",
    groceries_sponsored: "0",
    category: "groceries",
    remarks: "",
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await api<Entry[]>(`/api/petty-cash?year=${year}`));
      setSummary(await api(`/api/petty-cash/summary?year=${year}`));
      setError("");
    } finally {
      setLoading(false);
    }
  }, [year]);

  useEffect(() => {
    load().catch((err) => setError(err.message));
  }, [load]);

  async function save(event: FormEvent) {
    event.preventDefault();
    try {
      const body = {
        ...form,
        budgeted: Number(form.budgeted),
        actual: Number(form.actual),
        groceries_sponsored: Number(form.groceries_sponsored),
      };
      if (editingId) {
        await api(`/api/petty-cash/${editingId}`, { method: "PATCH", body: JSON.stringify(body) });
        setSuccess("Petty cash entry updated.");
      } else {
        await api("/api/petty-cash", { method: "POST", body: JSON.stringify(body) });
        setSuccess("Petty cash entry saved.");
      }
      setOpen(false);
      setEditingId(null);
      await load();
    } catch (err) {
      setError(formatError(err, "Unable to save"));
    }
  }

  return (
    <AppShell>
      <PageHeader
        title="Petty cash"
        subtitle="Balance is always budget minus actual and cannot be typed in."
        actions={canWrite ? (
          <button className="btn" onClick={() => {
            setEditingId(null);
            setForm({ month: "", budgeted: "", actual: "", groceries_sponsored: "0", category: "groceries", remarks: "" });
            setOpen(true);
          }}>Add month</button>
        ) : null}
      />
      {error ? <Banner kind="error">{error}</Banner> : null}
      {success ? <Banner kind="success">{success}</Banner> : null}
      {summary ? (
        <p className="muted">
          Budgeted RM {summary.total_budgeted} · Actual RM {summary.total_actual} · Balance RM {summary.total_balance}
        </p>
      ) : null}
      <div className="toolbar">
        <input type="number" min={2000} max={2100} value={year} onChange={(e) => setYear(e.target.value)} style={{ maxWidth: 140 }} aria-label="Year" />
      </div>
      <div className="card table-wrap">
        {loading || !rows ? <Loading>Loading petty cash…</Loading> : !rows.length ? <Empty>No petty cash entries yet.</Empty> : (
          <table>
            <thead>
              <tr>
                <th>Month</th><th>Category</th><th>Budgeted</th><th>Actual</th><th>Balance</th><th>Groceries sponsored</th>{canWrite ? <th></th> : null}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id}>
                  <td>{row.month.slice(0, 7)}</td>
                  <td>{row.category.replaceAll("_", " ")}</td>
                  <td>{row.budgeted}</td>
                  <td>{row.actual}</td>
                  <td>{row.balance}</td>
                  <td>{row.groceries_sponsored}</td>
                  {canWrite ? (
                    <td>
                      <button
                        className="btn secondary"
                        type="button"
                        onClick={() => {
                          setEditingId(row.id);
                          setForm({
                            month: row.month,
                            budgeted: row.budgeted,
                            actual: row.actual,
                            groceries_sponsored: row.groceries_sponsored,
                            category: row.category,
                            remarks: row.remarks || "",
                          });
                          setOpen(true);
                        }}
                      >
                        Edit
                      </button>
                      <ConfirmButton
                        label="Delete"
                        danger
                        message={`Delete petty cash entry for ${row.month.slice(0, 7)}?`}
                        onConfirm={async () => {
                          try {
                            await api(`/api/petty-cash/${row.id}`, { method: "DELETE" });
                            setSuccess("Petty cash entry deleted.");
                            await load();
                          } catch (err) {
                            setError(formatError(err, "Unable to delete"));
                          }
                        }}
                      />
                    </td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      {open && canWrite ? (
        <Modal title={editingId ? "Edit petty cash" : "Petty cash entry"} onClose={() => setOpen(false)}>
          <form className="form-grid" onSubmit={save}>
            <Field label="Month"><input type="date" required value={form.month} onChange={(e) => setForm({ ...form, month: e.target.value })} /></Field>
            <Field label="Category">
              <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
                {CATEGORIES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </Field>
            <Field label="Budgeted (RM)"><input type="number" min={0} step="0.01" required value={form.budgeted} onChange={(e) => setForm({ ...form, budgeted: e.target.value })} /></Field>
            <Field label="Actual (RM)"><input type="number" min={0} step="0.01" required value={form.actual} onChange={(e) => setForm({ ...form, actual: e.target.value })} /></Field>
            <Field label="Groceries sponsored (RM)"><input type="number" min={0} step="0.01" value={form.groceries_sponsored} onChange={(e) => setForm({ ...form, groceries_sponsored: e.target.value })} /></Field>
            <Field label="Remarks"><textarea value={form.remarks} onChange={(e) => setForm({ ...form, remarks: e.target.value })} /></Field>
            <button className="btn">Save</button>
          </form>
        </Modal>
      ) : null}
    </AppShell>
  );
}
