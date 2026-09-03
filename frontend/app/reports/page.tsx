"use client";

import { useState } from "react";
import { AppShell } from "@/components/AppShell";
import { Banner, PageHeader } from "@/components/ui";
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

export default function ReportsPage() {
  const today = new Date().toISOString().slice(0, 10);
  const monthStart = today.slice(0, 8) + "01";
  const [report, setReport] = useState("occupancy");
  const [start, setStart] = useState(monthStart);
  const [end, setEnd] = useState(today);
  const [data, setData] = useState<unknown>(null);
  const [error, setError] = useState("");

  async function run() {
    setError("");
    try {
      setData(await api(`/api/reports/${report}${qs({ start, end })}`));
    } catch (err) {
      setError(err instanceof HttpError ? err.message : "Unable to load report");
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
    link.download = `${report}.${format}`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <AppShell>
      <PageHeader title="Reports" subtitle="All figures are calculated on the server. Viewer accounts receive aggregated data only." />
      {error ? <Banner kind="error">{error}</Banner> : null}
      <div className="toolbar">
        <select value={report} onChange={(e) => setReport(e.target.value)} style={{ maxWidth: 280 }}>
          {REPORTS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
        <input type="date" value={start} onChange={(e) => setStart(e.target.value)} style={{ maxWidth: 180 }} />
        <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} style={{ maxWidth: 180 }} />
        <button className="btn" onClick={run}>Run</button>
        <button className="btn secondary" onClick={() => download("xlsx")}>Excel</button>
        <button className="btn secondary" onClick={() => download("pdf")}>PDF</button>
      </div>
      <div className="card">
        {data ? <pre style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(data, null, 2)}</pre> : <p className="muted">Choose a report and date range, then Run.</p>}
      </div>
    </AppShell>
  );
}
