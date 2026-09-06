"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { Banner, Empty, Loading, PageHeader } from "@/components/ui";
import { api, qs } from "@/lib/api";
import type { Page } from "@/lib/types";

type AuditItem = {
  id: number;
  user_name: string | null;
  entity: string;
  entity_id: number;
  action: string;
  changed_fields: string[] | null;
  timestamp: string;
};

export default function AuditPage() {
  const [data, setData] = useState<Page<AuditItem> | null>(null);
  const [error, setError] = useState("");
  const [entity, setEntity] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api<Page<AuditItem>>(`/api/audit-log${qs({ entity: entity || undefined, page })}`)
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [entity, page]);

  return (
    <AppShell>
      <PageHeader title="Audit log" subtitle="Read-only. Create, edit and delete of patients, stays, rooms, finance and users are recorded here." />
      {error ? <Banner kind="error">{error}</Banner> : null}
      <div className="toolbar">
        <select value={entity} onChange={(e) => { setEntity(e.target.value); setPage(1); }} style={{ maxWidth: 220 }} aria-label="Entity">
          <option value="">All entities</option>
          {["Patient", "Room", "RoomStay", "Donation", "PettyCashEntry", "MealSponsorship", "User", "WaitlistEntry"].map((name) => (
            <option key={name}>{name}</option>
          ))}
        </select>
      </div>
      <div className="card table-wrap">
        {loading && !data ? <Loading>Loading audit log…</Loading> : !data?.items.length ? <Empty>No audit records.</Empty> : (
          <table>
            <thead>
              <tr><th>When</th><th>User</th><th>Entity</th><th>ID</th><th>Action</th><th>Changed</th></tr>
            </thead>
            <tbody>
              {data.items.map((row) => (
                <tr key={row.id}>
                  <td>{row.timestamp}</td>
                  <td>{row.user_name || "—"}</td>
                  <td>{row.entity}</td>
                  <td>{row.entity_id}</td>
                  <td>{row.action}</td>
                  <td>{(row.changed_fields || []).join(", ")}</td>
                </tr>
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
