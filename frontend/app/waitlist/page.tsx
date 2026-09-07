"use client";

import { FormEvent, useEffect, useState } from "react";
import { AppShell, can, useUser } from "@/components/AppShell";
import { PatientPicker } from "@/components/PatientPicker";
import { Banner, Empty, Field, Loading, Modal, PageHeader } from "@/components/ui";
import { api, HttpError } from "@/lib/api";
import type { WaitlistEntry } from "@/lib/types";

export default function WaitlistPage() {
  const user = useUser();
  const [rows, setRows] = useState<WaitlistEntry[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [patientId, setPatientId] = useState("");
  const [remarks, setRemarks] = useState("");

  async function load() {
    setLoading(true);
    try {
      setRows(await api<WaitlistEntry[]>("/api/waitlist"));
      setError("");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load().catch((err) => setError(err.message));
  }, []);

  async function add(event: FormEvent) {
    event.preventDefault();
    try {
      await api("/api/waitlist", { method: "POST", body: JSON.stringify({ patient_id: Number(patientId), remarks }) });
      setOpen(false);
      await load();
    } catch (err) {
      setError(err instanceof HttpError ? err.message : "Unable to add");
    }
  }

  return (
    <AppShell>
      <PageHeader
        title="Waiting list"
        subtitle="Days waited are calculated from added and resolved dates."
        actions={
          can(user, "waitlist:write") ? (
            <button className="btn" onClick={() => setOpen(true)}>
              Add family
            </button>
          ) : null
        }
      />
      {error ? <Banner kind="error">{error}</Banner> : null}
      <div className="card table-wrap">
        {loading && !rows.length ? (
          <Loading>Loading waiting list…</Loading>
        ) : !rows.length ? (
          <Empty>No families currently waiting.</Empty>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Patient</th>
                <th>Registration</th>
                <th>Added</th>
                <th>Days waited</th>
                <th>Remarks</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id}>
                  <td>{row.patient_name}</td>
                  <td>{row.registration_no}</td>
                  <td>{row.added_date}</td>
                  <td>{row.days_waited}</td>
                  <td>{row.remarks || "—"}</td>
                  <td>
                    {can(user, "waitlist:write") ? (
                      <button
                        className="btn secondary"
                        onClick={async () => {
                          if (!window.confirm(`Resolve waiting-list entry for ${row.patient_name}?`)) return;
                          await api(`/api/waitlist/${row.id}/resolve`, { method: "POST" });
                          await load();
                        }}
                      >
                        Resolve
                      </button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      {open ? (
        <Modal title="Add to waiting list" onClose={() => setOpen(false)}>
          <form onSubmit={add} className="form-grid">
            <Field label="Patient">
              <PatientPicker value={patientId} onChange={setPatientId} />
            </Field>
            <Field label="Remarks">
              <textarea value={remarks} onChange={(e) => setRemarks(e.target.value)} />
            </Field>
            <button className="btn">Add</button>
          </form>
        </Modal>
      ) : null}
    </AppShell>
  );
}
