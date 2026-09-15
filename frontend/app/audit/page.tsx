"use client";

import { Fragment, useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { Banner, Empty, Loading, PageHeader } from "@/components/ui";
import { api, downloadFile, formatError, qs } from "@/lib/api";
import type { Page } from "@/lib/types";

type AuditItem = {
  id: number;
  user_name: string | null;
  entity: string;
  entity_id: number;
  action: string;
  changed_fields: string[] | null;
  before_values: Record<string, unknown> | null;
  after_values: Record<string, unknown> | null;
  timestamp: string;
};

export default function AuditPage() {
  const [data, setData] = useState<Page<AuditItem> | null>(null);
  const [error, setError] = useState("");
  const [entity, setEntity] = useState("");
  const [action, setAction] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [openId, setOpenId] = useState<number | null>(null);
  const [exporting, setExporting] = useState(false);
  const [success, setSuccess] = useState("");

  useEffect(() => {
    setLoading(true);
    api<Page<AuditItem>>(`/api/audit-log${qs({ entity: entity || undefined, action: action || undefined, start: start || undefined, end: end || undefined, page })}`)
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [entity, action, start, end, page]);

  return (
    <AppShell>
      <PageHeader
        title="Audit log"
        subtitle="Read-only. Create, edit and delete of patients, stays, rooms, finance and users are recorded here. Excel export includes metadata only — not before/after snapshots."
        actions={
          <button
            className="btn secondary"
            type="button"
            disabled={exporting}
            onClick={async () => {
              setExporting(true);
              try {
                await downloadFile(`/api/audit-log/export${qs({ entity: entity || undefined, action: action || undefined, start: start || undefined, end: end || undefined })}`, "RMH-HCTM-UKM-audit-log.xlsx");
                setSuccess("Audit metadata exported.");
              } catch (err) {
                setError(formatError(err, "Unable to export audit log"));
              } finally {
                setExporting(false);
              }
            }}
          >
            {exporting ? "Exporting…" : "Excel"}
          </button>
        }
      />
      {error ? <Banner kind="error">{error}</Banner> : null}
      {success ? <Banner kind="success">{success}</Banner> : null}
      <div className="toolbar">
        <select value={entity} onChange={(e) => { setEntity(e.target.value); setPage(1); }} style={{ maxWidth: 220 }} aria-label="Entity">
          <option value="">All entities</option>
          {["Patient", "Room", "RoomStay", "Donation", "PettyCashEntry", "MealSponsorship", "User", "WaitlistEntry", "WardClinic", "State", "DonationCategory"].map((name) => (
            <option key={name}>{name}</option>
          ))}
        </select>
        <select value={action} onChange={(e) => { setAction(e.target.value); setPage(1); }} style={{ maxWidth: 180 }} aria-label="Action">
          <option value="">All actions</option>
          {["create", "update", "delete", "check_in", "check_out", "resolve", "activate", "deactivate", "login", "login_failed", "logout"].map((name) => (
            <option key={name} value={name}>{name.replaceAll("_", " ")}</option>
          ))}
        </select>
        <input type="date" value={start} onChange={(e) => { setStart(e.target.value); setPage(1); }} style={{ maxWidth: 170 }} aria-label="From date" />
        <input type="date" value={end} onChange={(e) => { setEnd(e.target.value); setPage(1); }} style={{ maxWidth: 170 }} aria-label="To date" />
      </div>
      <div className="card table-wrap">
        {loading && !data ? <Loading>Loading audit log…</Loading> : !data?.items.length ? <Empty>No audit records.</Empty> : (
          <table>
            <thead>
              <tr><th>When</th><th>User</th><th>Entity</th><th>ID</th><th>Action</th><th>Changed</th></tr>
            </thead>
            <tbody>
              {data.items.map((row) => (
                <Fragment key={row.id}>
                <tr>
                  <td>{row.timestamp}</td>
                  <td>{row.user_name || "—"}</td>
                  <td>{row.entity}</td>
                  <td>{row.entity_id}</td>
                  <td>{row.action}</td>
                  <td>
                    {(row.changed_fields || []).join(", ") || "—"}
                    <button className="btn secondary" type="button" style={{ marginLeft: 8 }} onClick={() => setOpenId(openId === row.id ? null : row.id)}>
                      {openId === row.id ? "Hide" : "Values"}
                    </button>
                  </td>
                </tr>
                {openId === row.id ? (
                  <tr>
                    <td colSpan={6}>
                      <div className="grid" style={{ gridTemplateColumns: "1fr 1fr" }}>
                        <div>
                          <strong>Before</strong>
                          <pre className="muted" style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(row.before_values, null, 2) || "—"}</pre>
                        </div>
                        <div>
                          <strong>After</strong>
                          <pre className="muted" style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(row.after_values, null, 2) || "—"}</pre>
                        </div>
                      </div>
                    </td>
                  </tr>
                ) : null}
                </Fragment>
              ))}
            </tbody>
          </table>
        )}
        <div className="pagination">
          <button className="btn secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Previous</button>
          <span>Page {data?.page ?? 1} of {data?.pages || 1} · {data?.total ?? 0} records</span>
          <button className="btn secondary" disabled={(data?.page ?? 1) >= (data?.pages || 1)} onClick={() => setPage((p) => p + 1)}>Next</button>
        </div>
      </div>
    </AppShell>
  );
}
