"use client";

import { useState } from "react";
import { AppShell } from "@/components/AppShell";
import { Banner, Empty, Loading, PageHeader } from "@/components/ui";
import { api, HttpError, qs } from "@/lib/api";

const REPORTS = [
  ["occupancy", "Daily occupancy rate"],
  ["occupancy-trend", "Occupancy trend"],
  ["census", "Patient census"],
  ["census-gender", "Census by gender"],
  ["census-ward", "Census by ward"],
  ["census-state", "Census by state"],
  ["new-vs-returning", "New vs returning"],
  ["guardian-sibling", "Guardian / sibling totals"],
  ["length-of-stay", "Length of stay"],
  ["room-rental-income", "Room rental income"],
  ["donations-summary", "Donation summary"],
  ["petty-cash", "Petty cash budget vs actual"],
  ["admission-summary", "Admission summary"],
];

function summaryEntries(data: Record<string, unknown>) {
  return Object.entries(data).filter(([, value]) => !Array.isArray(value) && (typeof value !== "object" || value === null));
}

function tableFromReport(data: Record<string, unknown>): { headers: string[]; rows: string[][] } | null {
  for (const key of ["days", "trend", "groups"]) {
    const items = data[key];
    if (Array.isArray(items) && items.length && typeof items[0] === "object") {
      const headers = Object.keys(items[0] as object);
      const rows = (items as Record<string, unknown>[]).map((row) => headers.map((h) => String(row[h] ?? "")));
      return { headers, rows };
    }
  }
  if (data.by_category && typeof data.by_category === "object") {
    const entries = Object.entries(data.by_category as Record<string, unknown>);
    if (!entries.length) return null;
    const first = entries[0][1];
    if (first && typeof first === "object") {
      const headers = ["category", ...Object.keys(first as object)];
      const rows = entries.map(([cat, vals]) => [cat, ...Object.values(vals as object).map((v) => String(v))]);
      return { headers, rows };
    }
    return { headers: ["category", "amount"], rows: entries.map(([k, v]) => [k, String(v)]) };
  }
  if (data.by_type && typeof data.by_type === "object") {
    return {
      headers: ["type", "amount"],
      rows: Object.entries(data.by_type as Record<string, unknown>).map(([k, v]) => [k, String(v)]),
    };
  }
  if (data.by_meal_type && typeof data.by_meal_type === "object") {
    return {
      headers: ["meal type", "amount"],
      rows: Object.entries(data.by_meal_type as Record<string, unknown>).map(([k, v]) => [k, String(v)]),
    };
  }
  return null;
}

function ReportView({ data }: { data: Record<string, unknown> }) {
  const table = tableFromReport(data);
  const summary = summaryEntries(data);
  return (
    <div>
      <div className="grid stats" style={{ marginBottom: 16 }}>
        {summary.map(([key, value]) => (
          <div className="card" key={key}>
            <div className="muted">{key.replaceAll("_", " ")}</div>
            <div className="stat-value" style={{ fontSize: "1.15rem" }}>{String(value)}</div>
          </div>
        ))}
      </div>
      {table ? (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                {table.headers.map((header) => (
                  <th key={header}>{header.replaceAll("_", " ")}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {table.rows.map((row, idx) => (
                <tr key={idx}>
                  {row.map((cell, cellIdx) => (
                    <td key={cellIdx}>{cell}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <Empty>No tabulated rows for this period.</Empty>
      )}
    </div>
  );
}

export default function ReportsPage() {
  const today = new Date().toISOString().slice(0, 10);
  const monthStart = today.slice(0, 8) + "01";
  const [report, setReport] = useState("occupancy");
  const [start, setStart] = useState(monthStart);
  const [end, setEnd] = useState(today);
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function run() {
    setError("");
    setLoading(true);
    try {
      setData(await api<Record<string, unknown>>(`/api/reports/${report}${qs({ start, end })}`));
    } catch (err) {
      setError(err instanceof HttpError ? err.message : "Unable to load report");
    } finally {
      setLoading(false);
    }
  }

  async function download(format: "xlsx" | "pdf") {
    const response = await fetch(`/api/reports/${report}/export${qs({ start, end, format })}`, {
      credentials: "include",
    });
    if (!response.ok) {
      setError("Export failed or is not permitted for this role.");
      return;
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `RMH-HCTM-UKM-${report}.${format}`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <AppShell>
      <PageHeader title="Reports" subtitle="All figures are calculated on the server. Viewer accounts receive aggregated data only — no patient identifiers." />
      {error ? <Banner kind="error">{error}</Banner> : null}
      <div className="toolbar">
        <select value={report} onChange={(e) => setReport(e.target.value)} style={{ maxWidth: 280 }} aria-label="Report">
          {REPORTS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
        <input type="date" value={start} onChange={(e) => setStart(e.target.value)} style={{ maxWidth: 180 }} aria-label="Start date" />
        <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} style={{ maxWidth: 180 }} aria-label="End date" />
        <button className="btn" onClick={run} disabled={loading}>{loading ? "Running…" : "Run"}</button>
        <button className="btn secondary" onClick={() => download("xlsx")}>Excel</button>
        <button className="btn secondary" onClick={() => download("pdf")}>PDF</button>
      </div>
      <div className="card">
        {loading ? <Loading>Calculating report…</Loading> : null}
        {data && !loading ? <ReportView data={data} /> : !loading ? <p className="muted">Choose a report and date range, then Run.</p> : null}
      </div>
    </AppShell>
  );
}
