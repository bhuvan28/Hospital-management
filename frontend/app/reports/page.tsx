"use client";

import { useEffect, useState } from "react";
import { AppShell, can, useUser } from "@/components/AppShell";
import { Banner, Empty, Loading, PageHeader } from "@/components/ui";
import { api, downloadFile, formatError, qs } from "@/lib/api";
import type { Lookup } from "@/lib/types";

const REPORTS: [string, string, string][] = [
  ["occupancy", "Daily occupancy rate", "reports:occupancy"],
  ["occupancy-trend", "Occupancy trend", "reports:occupancy"],
  ["census", "Patient census", "reports:census"],
  ["census-gender", "Census by gender", "reports:census"],
  ["census-ward", "Census by ward", "reports:census"],
  ["census-state", "Census by state", "reports:census"],
  ["new-vs-returning", "New vs returning", "reports:census"],
  ["guardian-sibling", "Guardian / sibling totals", "reports:census"],
  ["length-of-stay", "Length of stay", "reports:occupancy"],
  ["room-rental-income", "Room rental income", "reports:finance"],
  ["donations-summary", "Donation summary", "reports:finance"],
  ["petty-cash", "Petty cash budget vs actual", "reports:finance"],
  ["admission-summary", "Admission summary", "reports:admission"],
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

const CENSUS_FILTERS = new Set([
  "census",
  "census-gender",
  "census-ward",
  "census-state",
  "new-vs-returning",
  "guardian-sibling",
  "room-rental-income",
]);

export default function ReportsPage() {
  const user = useUser();
  const today = new Date().toISOString().slice(0, 10);
  const monthStart = today.slice(0, 8) + "01";
  const available = REPORTS.filter(([, , permission]) => can(user, permission));
  const [report, setReport] = useState(available[0]?.[0] || "occupancy");
  const [start, setStart] = useState(monthStart);
  const [end, setEnd] = useState(today);
  const [grain, setGrain] = useState("month");
  const [ward, setWard] = useState("");
  const [stateId, setStateId] = useState("");
  const [status, setStatus] = useState("");
  const [gender, setGender] = useState("");
  const [wards, setWards] = useState<Lookup[]>([]);
  const [states, setStates] = useState<Lookup[]>([]);
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState<"xlsx" | "pdf" | "">("");

  useEffect(() => {
    api<Lookup[]>("/api/lookups/wards").then(setWards).catch(() => undefined);
    api<Lookup[]>("/api/lookups/states").then(setStates).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!available.length) return;
    let cancelled = false;
    setLoading(true);
    setError("");
    api<Record<string, unknown>>(`/api/reports/${report}${query()}`)
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err) => {
        if (!cancelled) setError(formatError(err, "Unable to load report"));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // query() is derived from the filter state listed below
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [report, start, end, grain, ward, stateId, status, gender]);

  function query(extra: Record<string, string | undefined> = {}) {
    return qs({
      start,
      end,
      grain: report === "occupancy-trend" ? grain : undefined,
      ward_clinic_id: CENSUS_FILTERS.has(report) ? ward || undefined : undefined,
      state_id: CENSUS_FILTERS.has(report) ? stateId || undefined : undefined,
      status: CENSUS_FILTERS.has(report) ? status || undefined : undefined,
      gender: CENSUS_FILTERS.has(report) ? gender || undefined : undefined,
      ...extra,
    });
  }

  async function run() {
    setError("");
    setLoading(true);
    try {
      setData(await api<Record<string, unknown>>(`/api/reports/${report}${query()}`));
    } catch (err) {
      setError(formatError(err, "Unable to load report"));
    } finally {
      setLoading(false);
    }
  }

  async function download(format: "xlsx" | "pdf") {
    if (exporting) return;
    setExporting(format);
    setError("");
    try {
      await downloadFile(`/api/reports/${report}/export${query({ format })}`, `RMH-HCTM-UKM-${report}.${format}`);
      setSuccess(`Exported ${report} as ${format.toUpperCase()}.`);
    } catch (err) {
      setError(formatError(err, "Export failed or is not permitted for this role."));
    } finally {
      setExporting("");
    }
  }

  return (
    <AppShell>
      <PageHeader title="Reports" subtitle="All figures are calculated on the server. Viewer accounts receive aggregated data only — no patient identifiers." />
      {error ? <Banner kind="error">{error}</Banner> : null}
      {success ? <Banner kind="success">{success}</Banner> : null}
      <div className="toolbar">
        <select value={report} onChange={(e) => setReport(e.target.value)} style={{ maxWidth: 280 }} aria-label="Report">
          {available.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
        <input type="date" value={start} onChange={(e) => setStart(e.target.value)} style={{ maxWidth: 180 }} aria-label="Start date" />
        <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} style={{ maxWidth: 180 }} aria-label="End date" />
        {report === "occupancy-trend" ? (
          <select value={grain} onChange={(e) => setGrain(e.target.value)} style={{ maxWidth: 160 }} aria-label="Trend grain">
            <option value="month">Monthly</option>
            <option value="year">Annual</option>
          </select>
        ) : null}
        {CENSUS_FILTERS.has(report) ? (
          <>
            <select value={ward} onChange={(e) => setWard(e.target.value)} style={{ maxWidth: 220 }} aria-label="Ward filter">
              <option value="">All wards</option>
              {wards.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select>
            <select value={stateId} onChange={(e) => setStateId(e.target.value)} style={{ maxWidth: 200 }} aria-label="State filter">
              <option value="">All states</option>
              {states.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select>
            <select value={status} onChange={(e) => setStatus(e.target.value)} style={{ maxWidth: 160 }} aria-label="Status filter">
              <option value="">All statuses</option>
              <option value="new">New</option>
              <option value="returning">Returning</option>
            </select>
            <select value={gender} onChange={(e) => setGender(e.target.value)} style={{ maxWidth: 160 }} aria-label="Gender filter">
              <option value="">All genders</option>
              <option value="female">Female</option>
              <option value="male">Male</option>
              <option value="other">Other</option>
              <option value="unspecified">Unspecified</option>
            </select>
          </>
        ) : null}
        <button className="btn" onClick={run} disabled={loading}>{loading ? "Running…" : "Run"}</button>
        <button className="btn secondary" onClick={() => download("xlsx")} disabled={!!exporting}>{exporting === "xlsx" ? "Exporting…" : "Excel"}</button>
        <button className="btn secondary" onClick={() => download("pdf")} disabled={!!exporting}>{exporting === "pdf" ? "Exporting…" : "PDF"}</button>
      </div>
      <div className="card">
        {loading ? <Loading>Calculating report…</Loading> : null}
        {data && !loading ? <ReportView data={data} /> : !loading ? <Empty>No report rows for this period.</Empty> : null}
      </div>
    </AppShell>
  );
}
