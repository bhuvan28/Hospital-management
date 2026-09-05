"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { Banner, Empty, PageHeader } from "@/components/ui";
import { api } from "@/lib/api";

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
  const [data, setData] = useState<{ items: AuditItem[]; total: number } | null>(null);
  const [error, setError] = useState("");
  const [entity, setEntity] = useState("");

  useEffect(() => {
    api<{ items: AuditItem[]; total: number }>(`/api/audit-log${entity ? `?entity=${entity}` : ""}`)
      .then(setData)
      .catch((err) => setError(err.message));
  }, [entity]);

  return (
    <AppShell>
      <PageHeader title="Audit log" subtitle="Read-only. Create, edit and delete of patients, stays, rooms, finance and users are recorded here." />
      {error ? <Banner kind="error">{error}</Banner> : null}
      <div className="toolbar">
        <select value={entity} onChange={(e) => setEntity(e.target.value)} style={{ maxWidth: 220 }}>
          <option value="">All entities</option>
          {["Patient", "Room", "RoomStay", "Donation", "PettyCashEntry", "MealSponsorship", "User", "WaitlistEntry"].map((name) => (
            <option key={name}>{name}</option>
          ))}
        </select>
      </div>
      <div className="card table-wrap">
        {!data?.items.length ? <Empty>No audit records.</Empty> : (
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
      </div>
    </AppShell>
  );
}
