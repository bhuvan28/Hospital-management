"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { AppShell, can, useUser } from "@/components/AppShell";
import { Banner, ConfirmButton, Empty, Field, Loading, Modal, PageHeader } from "@/components/ui";
import { api, formatError, qs } from "@/lib/api";
import type { Page } from "@/lib/types";

type Meal = {
  id: number;
  date: string;
  sponsor_name: string;
  item_remark: string | null;
  meal_type: string;
  pax: number;
  amount: string;
};

const MEALS = ["breakfast", "lunch", "hi_tea", "dinner"];

export default function MealsPage() {
  const user = useUser();
  const canWrite = can(user, "meals:write");
  const [rows, setRows] = useState<Page<Meal> | null>(null);
  const [summary, setSummary] = useState<{ monthly_total: string; total_pax: number } | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [open, setOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [mealType, setMealType] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({
    date: "",
    sponsor_name: "",
    item_remark: "",
    meal_type: "lunch",
    pax: 0,
    amount: "",
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await api<Page<Meal>>(`/api/meal-sponsorships${qs({ start: start || undefined, end: end || undefined, meal_type: mealType || undefined, page })}`));
      setSummary(await api(`/api/meal-sponsorships/summary${qs({ start: start || undefined, end: end || undefined })}`));
      setError("");
    } finally {
      setLoading(false);
    }
  }, [start, end, mealType, page]);

  useEffect(() => {
    load().catch((err) => setError(err.message));
  }, [load]);

  async function save(event: FormEvent) {
    event.preventDefault();
    try {
      const body = { ...form, pax: Number(form.pax), amount: Number(form.amount) };
      if (editingId) {
        await api(`/api/meal-sponsorships/${editingId}`, { method: "PATCH", body: JSON.stringify(body) });
        setSuccess("Meal sponsorship updated.");
      } else {
        await api("/api/meal-sponsorships", { method: "POST", body: JSON.stringify(body) });
        setSuccess("Meal sponsorship recorded.");
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
        title="Meal sponsorship"
        subtitle="Breakfast, lunch, hi-tea and dinner sponsorships."
        actions={canWrite ? (
          <button className="btn" onClick={() => {
            setEditingId(null);
            setForm({ date: "", sponsor_name: "", item_remark: "", meal_type: "lunch", pax: 0, amount: "" });
            setOpen(true);
          }}>Record sponsorship</button>
        ) : null}
      />
      {error ? <Banner kind="error">{error}</Banner> : null}
      {success ? <Banner kind="success">{success}</Banner> : null}
      {summary ? <p className="muted">{start || end ? "Filtered" : "This month"} RM {summary.monthly_total} · {summary.total_pax} pax in range</p> : null}
      <div className="toolbar">
        <select value={mealType} onChange={(e) => { setMealType(e.target.value); setPage(1); }} style={{ maxWidth: 200 }} aria-label="Meal type">
          <option value="">All meals</option>
          {MEALS.map((m) => <option key={m} value={m}>{m.replace("_", "-")}</option>)}
        </select>
        <input type="date" value={start} onChange={(e) => { setStart(e.target.value); setPage(1); }} style={{ maxWidth: 170 }} aria-label="From date" />
        <input type="date" value={end} onChange={(e) => { setEnd(e.target.value); setPage(1); }} style={{ maxWidth: 170 }} aria-label="To date" />
      </div>
      <div className="card table-wrap">
        {loading && !rows ? <Loading>Loading meal sponsorships…</Loading> : !rows?.items.length ? <Empty>No meal sponsorships yet.</Empty> : (
          <table>
            <thead>
              <tr><th>Date</th><th>Sponsor</th><th>Meal</th><th>Pax</th><th>Amount (RM)</th><th>Item</th>{canWrite ? <th></th> : null}</tr>
            </thead>
            <tbody>
              {rows.items.map((row) => (
                <tr key={row.id}>
                  <td>{row.date}</td>
                  <td>{row.sponsor_name}</td>
                  <td>{row.meal_type.replace("_", "-")}</td>
                  <td>{row.pax}</td>
                  <td>{row.amount}</td>
                  <td>{row.item_remark}</td>
                  {canWrite ? (
                    <td>
                      <button
                        className="btn secondary"
                        type="button"
                        onClick={() => {
                          setEditingId(row.id);
                          setForm({
                            date: row.date,
                            sponsor_name: row.sponsor_name,
                            item_remark: row.item_remark || "",
                            meal_type: row.meal_type,
                            pax: row.pax,
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
                        message={`Delete sponsorship from ${row.sponsor_name}?`}
                        onConfirm={async () => {
                          try {
                            await api(`/api/meal-sponsorships/${row.id}`, { method: "DELETE" });
                            setSuccess("Meal sponsorship deleted.");
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
        <div className="pagination">
          <button className="btn secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Previous</button>
          <span>Page {rows?.page ?? 1} of {rows?.pages || 1} · {rows?.total ?? 0} records</span>
          <button className="btn secondary" disabled={(rows?.page ?? 1) >= (rows?.pages || 1)} onClick={() => setPage((p) => p + 1)}>Next</button>
        </div>
      </div>
      {open && canWrite ? (
        <Modal title={editingId ? "Edit meal sponsorship" : "Meal sponsorship"} onClose={() => setOpen(false)}>
          <form className="form-grid" onSubmit={save}>
            <Field label="Date"><input type="date" required value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} /></Field>
            <Field label="Sponsor"><input required value={form.sponsor_name} onChange={(e) => setForm({ ...form, sponsor_name: e.target.value })} /></Field>
            <Field label="Meal type">
              <select value={form.meal_type} onChange={(e) => setForm({ ...form, meal_type: e.target.value })}>
                {MEALS.map((m) => <option key={m} value={m}>{m.replace("_", "-")}</option>)}
              </select>
            </Field>
            <Field label="Pax"><input type="number" min={0} value={form.pax} onChange={(e) => setForm({ ...form, pax: Number(e.target.value) })} /></Field>
            <Field label="Amount (RM)"><input type="number" min={0} step="0.01" required value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} /></Field>
            <Field label="Item / remark"><textarea value={form.item_remark} onChange={(e) => setForm({ ...form, item_remark: e.target.value })} /></Field>
            <button className="btn">Save</button>
          </form>
        </Modal>
      ) : null}
    </AppShell>
  );
}
