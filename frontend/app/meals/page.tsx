"use client";

import { FormEvent, useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { Banner, Empty, Field, Modal, PageHeader } from "@/components/ui";
import { api, HttpError } from "@/lib/api";
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
  const [rows, setRows] = useState<Page<Meal> | null>(null);
  const [summary, setSummary] = useState<{ monthly_total: string; total_pax: number } | null>(null);
  const [error, setError] = useState("");
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    date: "",
    sponsor_name: "",
    item_remark: "",
    meal_type: "lunch",
    pax: 18,
    amount: "",
  });

  async function load() {
    setRows(await api<Page<Meal>>("/api/meal-sponsorships"));
    setSummary(await api("/api/meal-sponsorships/summary"));
  }

  useEffect(() => {
    load().catch((err) => setError(err.message));
  }, []);

  async function create(event: FormEvent) {
    event.preventDefault();
    try {
      await api("/api/meal-sponsorships", {
        method: "POST",
        body: JSON.stringify({ ...form, pax: Number(form.pax), amount: Number(form.amount) }),
      });
      setOpen(false);
      await load();
    } catch (err) {
      setError(err instanceof HttpError ? err.message : "Unable to save");
    }
  }

  return (
    <AppShell>
      <PageHeader title="Meal sponsorship" subtitle="Breakfast, lunch, hi-tea and dinner sponsorships." actions={<button className="btn" onClick={() => setOpen(true)}>Record sponsorship</button>} />
      {error ? <Banner kind="error">{error}</Banner> : null}
      {summary ? <p className="muted">This month RM {summary.monthly_total} · {summary.total_pax} pax year to date</p> : null}
      <div className="card table-wrap">
        {!rows?.items.length ? <Empty>No meal sponsorships yet.</Empty> : (
          <table>
            <thead>
              <tr><th>Date</th><th>Sponsor</th><th>Meal</th><th>Pax</th><th>Amount (RM)</th><th>Item</th></tr>
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
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      {open ? (
        <Modal title="Meal sponsorship" onClose={() => setOpen(false)}>
          <form className="form-grid" onSubmit={create}>
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
