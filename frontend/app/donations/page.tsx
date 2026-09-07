"use client";

import { FormEvent, useEffect, useState } from "react";
import { AppShell, can, useUser } from "@/components/AppShell";
import { Banner, ConfirmButton, Empty, Field, Loading, Modal, PageHeader } from "@/components/ui";
import { api, HttpError, qs } from "@/lib/api";
import type { Lookup, Page } from "@/lib/types";

type Donation = {
  id: number;
  date: string;
  donor_name: string;
  type: string;
  category_name: string | null;
  item_remark: string | null;
  quantity: number;
  amount: string;
  category_id?: number | null;
};

const TYPES = ["cash", "in_kind", "event", "corporate", "rmh_family", "volunteer"];

export default function DonationsPage() {
  const user = useUser();
  const canWrite = can(user, "donations:write");
  const [rows, setRows] = useState<Page<Donation> | null>(null);
  const [summary, setSummary] = useState<{ monthly_total: string; annual_total: string } | null>(null);
  const [categories, setCategories] = useState<Lookup[]>([]);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [open, setOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [q, setQ] = useState("");
  const [type, setType] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({
    date: "",
    donor_name: "",
    type: "cash",
    category_id: "",
    item_remark: "",
    quantity: 1,
    amount: "0",
  });

  async function load() {
    setLoading(true);
    try {
      const [result, totals, cats] = await Promise.all([
        api<Page<Donation>>(`/api/donations${qs({ q, donation_type: type || undefined, category_id: categoryId || undefined, start: start || undefined, end: end || undefined, page })}`),
        api<{ monthly_total: string; annual_total: string }>("/api/donations/summary"),
        api<Lookup[]>("/api/lookups/donation-categories"),
      ]);
      setRows(result);
      setSummary(totals);
      setCategories(cats);
      setError("");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load().catch((err) => setError(err.message));
  }, [q, type, categoryId, start, end, page]);

  async function save(event: FormEvent) {
    event.preventDefault();
    try {
      const body = {
        ...form,
        category_id: form.category_id ? Number(form.category_id) : null,
        quantity: Number(form.quantity),
        amount: Number(form.amount),
      };
      if (editingId) {
        await api(`/api/donations/${editingId}`, { method: "PATCH", body: JSON.stringify(body) });
        setSuccess("Donation updated.");
      } else {
        await api("/api/donations", { method: "POST", body: JSON.stringify(body) });
        setSuccess("Donation recorded.");
      }
      setOpen(false);
      setEditingId(null);
      await load();
    } catch (err) {
      setError(err instanceof HttpError ? err.message : "Unable to save donation");
    }
  }

  return (
    <AppShell>
      <PageHeader
        title="Donations"
        subtitle="House-level records only. Donations are not linked to individual families in v1."
        actions={canWrite ? (
          <button className="btn" onClick={() => {
            setEditingId(null);
            setForm({ date: "", donor_name: "", type: "cash", category_id: "", item_remark: "", quantity: 1, amount: "0" });
            setOpen(true);
          }}>Record donation</button>
        ) : null}
      />
      {error ? <Banner kind="error">{error}</Banner> : null}
      {success ? <Banner kind="success">{success}</Banner> : null}
      {summary ? (
        <p className="muted">
          This month RM {summary.monthly_total} · This year RM {summary.annual_total}
        </p>
      ) : null}
      <div className="toolbar">
        <input placeholder="Search donor" value={q} onChange={(e) => setQ(e.target.value)} style={{ maxWidth: 240 }} aria-label="Search donor" />
        <select value={type} onChange={(e) => { setType(e.target.value); setPage(1); }} style={{ maxWidth: 200 }} aria-label="Filter by type">
          <option value="">All types</option>
          {TYPES.map((item) => (
            <option key={item} value={item}>{item.replace("_", " ")}</option>
          ))}
        </select>
        <select value={categoryId} onChange={(e) => { setCategoryId(e.target.value); setPage(1); }} style={{ maxWidth: 220 }} aria-label="Filter by category">
          <option value="">All categories</option>
          {categories.map((item) => (
            <option key={item.id} value={item.id}>{item.name}</option>
          ))}
        </select>
        <input type="date" value={start} onChange={(e) => setStart(e.target.value)} style={{ maxWidth: 170 }} aria-label="From date" />
        <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} style={{ maxWidth: 170 }} aria-label="To date" />
      </div>
      <div className="card table-wrap">
        {loading && !rows ? <Loading>Loading donations…</Loading> : !rows?.items.length ? <Empty>No donations recorded.</Empty> : (
          <table>
            <thead>
              <tr>
                <th>Date</th><th>Donor</th><th>Type</th><th>Category</th><th>Qty</th><th>Amount (RM)</th>{canWrite ? <th></th> : null}
              </tr>
            </thead>
            <tbody>
              {rows.items.map((row) => (
                <tr key={row.id}>
                  <td>{row.date}</td>
                  <td>{row.donor_name}</td>
                  <td>{row.type.replace("_", " ")}</td>
                  <td>{row.category_name || "—"}</td>
                  <td>{row.quantity}</td>
                  <td>{row.amount}</td>
                  {canWrite ? (
                    <td>
                      <button
                        className="btn secondary"
                        type="button"
                        onClick={() => {
                          setEditingId(row.id);
                          setForm({
                            date: row.date,
                            donor_name: row.donor_name,
                            type: row.type,
                            category_id: row.category_id ? String(row.category_id) : "",
                            item_remark: row.item_remark || "",
                            quantity: row.quantity,
                            amount: row.amount,
                          });
                          setOpen(true);
                        }}
                      >
                        Edit
                      </button>
                      <ConfirmButton
                        label="Delete"
                        danger
                        message={`Delete donation from ${row.donor_name}?`}
                        onConfirm={async () => {
                          try {
                            await api(`/api/donations/${row.id}`, { method: "DELETE" });
                            setSuccess("Donation deleted.");
                            await load();
                          } catch (err) {
                            setError(err instanceof HttpError ? err.message : "Unable to delete");
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
        <div className="pagination">
          <button className="btn secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Previous</button>
          <span>Page {rows?.page ?? 1} of {rows?.pages || 1} · {rows?.total ?? 0} records</span>
          <button className="btn secondary" disabled={(rows?.page ?? 1) >= (rows?.pages || 1)} onClick={() => setPage((p) => p + 1)}>Next</button>
        </div>
      </div>
      {open && canWrite ? (
        <Modal title={editingId ? "Edit donation" : "New donation"} onClose={() => setOpen(false)}>
          <form className="form-grid" onSubmit={save}>
            <Field label="Date"><input type="date" required value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} /></Field>
            <Field label="Donor / company"><input required value={form.donor_name} onChange={(e) => setForm({ ...form, donor_name: e.target.value })} /></Field>
            <Field label="Type">
              <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
                {TYPES.map((item) => <option key={item} value={item}>{item.replace("_", " ")}</option>)}
              </select>
            </Field>
            <Field label="Category">
              <select value={form.category_id} onChange={(e) => setForm({ ...form, category_id: e.target.value })}>
                <option value="">None</option>
                {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </Field>
            <Field label="Quantity"><input type="number" min={0} value={form.quantity} onChange={(e) => setForm({ ...form, quantity: Number(e.target.value) })} /></Field>
            <Field label="Amount (RM)"><input type="number" min={0} step="0.01" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} /></Field>
            <Field label="Item / remark"><textarea value={form.item_remark} onChange={(e) => setForm({ ...form, item_remark: e.target.value })} /></Field>
            <button className="btn">Save</button>
          </form>
        </Modal>
      ) : null}
    </AppShell>
  );
}
