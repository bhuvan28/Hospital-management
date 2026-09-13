"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { AppShell, can, useUser } from "@/components/AppShell";
import { PatientPicker } from "@/components/PatientPicker";
import { Banner, Empty, Field, Loading, Modal, PageHeader } from "@/components/ui";
import { api, formatError, qs } from "@/lib/api";
import { occupancyStatus, type Room, type WaitlistEntry } from "@/lib/types";

export default function WaitlistPage() {
  const user = useUser();
  const [rows, setRows] = useState<WaitlistEntry[]>([]);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [patientId, setPatientId] = useState("");
  const [remarks, setRemarks] = useState("");
  const [addedDate, setAddedDate] = useState("");
  const [saving, setSaving] = useState(false);
  const [q, setQ] = useState("");
  const [search, setSearch] = useState("");
  const [includeResolved, setIncludeResolved] = useState(false);
  const [checkInEntry, setCheckInEntry] = useState<WaitlistEntry | null>(null);
  const [vacantRooms, setVacantRooms] = useState<Room[]>([]);
  const [checkInRoomId, setCheckInRoomId] = useState("");
  const [checkInDate, setCheckInDate] = useState("");
  const [inspected, setInspected] = useState(false);
  const [checkInRemarks, setCheckInRemarks] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await api<WaitlistEntry[]>(`/api/waitlist${qs({ q: search || undefined, include_resolved: includeResolved ? "true" : undefined })}`));
      setError("");
    } finally {
      setLoading(false);
    }
  }, [search, includeResolved]);

  useEffect(() => {
    const handle = setTimeout(() => setSearch(q), 300);
    return () => clearTimeout(handle);
  }, [q]);

  useEffect(() => {
    load().catch((err) => setError(err.message));
  }, [load]);

  async function add(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      await api("/api/waitlist", {
        method: "POST",
        body: JSON.stringify({
          patient_id: Number(patientId),
          remarks,
          added_date: addedDate || null,
        }),
      });
      setOpen(false);
      setPatientId("");
      setRemarks("");
      setAddedDate("");
      setSuccess("Family added to the waiting list.");
      await load();
    } catch (err) {
      setError(formatError(err, "Unable to add"));
    } finally {
      setSaving(false);
    }
  }

  async function openCheckIn(entry: WaitlistEntry) {
    setCheckInEntry(entry);
    setCheckInDate(new Date().toISOString().slice(0, 10));
    setInspected(false);
    setCheckInRemarks(entry.remarks || "");
    setCheckInRoomId("");
    try {
      const rooms = await api<Room[]>("/api/rooms?occupancy_status=vacant");
      setVacantRooms(rooms.filter((room) => occupancyStatus(room) === "vacant"));
    } catch (err) {
      setError(formatError(err, "Unable to load vacant rooms"));
      setVacantRooms([]);
    }
  }

  async function submitWaitlistCheckIn(event: FormEvent) {
    event.preventDefault();
    if (!checkInEntry || !checkInRoomId) return;
    setSaving(true);
    try {
      await api(`/api/rooms/${checkInRoomId}/check-in`, {
        method: "POST",
        body: JSON.stringify({
          patient_id: checkInEntry.patient_id,
          check_in_date: checkInDate || null,
          room_inspected: inspected,
          remarks: checkInRemarks || null,
        }),
      });
      setSuccess(`Checked ${checkInEntry.patient_name} in. Waiting-list entry resolved.`);
      setCheckInEntry(null);
      await load();
    } catch (err) {
      setError(formatError(err, "Unable to check in"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <AppShell>
      <PageHeader
        title="Waiting list"
        subtitle="Days waited are calculated from added and resolved dates. Duty officers can check a waiting family into a vacant room in one step."
        actions={
          can(user, "waitlist:write") ? (
            <button className="btn" onClick={() => setOpen(true)}>
              Add family
            </button>
          ) : null
        }
      />
      {error ? <Banner kind="error">{error}</Banner> : null}
      {success ? <Banner kind="success">{success}</Banner> : null}
      <div className="toolbar">
        <input placeholder="Search name or registration no." value={q} onChange={(e) => setQ(e.target.value)} style={{ maxWidth: 280 }} aria-label="Search waiting list" />
        <label className="muted" style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <input type="checkbox" checked={includeResolved} onChange={(e) => setIncludeResolved(e.target.checked)} />
          Include resolved
        </label>
      </div>
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
                <th>Resolved</th>
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
                  <td>{row.resolved_date || "Open"}</td>
                  <td>{row.remarks || "—"}</td>
                  <td>
                    {can(user, "stays:check_in") && !row.resolved_date ? (
                      <button className="btn" type="button" onClick={() => openCheckIn(row)}>
                        Check in
                      </button>
                    ) : null}
                    {can(user, "waitlist:write") && !row.resolved_date ? (
                      <button
                        className="btn secondary"
                        onClick={async () => {
                          if (!window.confirm(`Resolve waiting-list entry for ${row.patient_name}?`)) return;
                          try {
                            await api(`/api/waitlist/${row.id}/resolve`, { method: "POST" });
                            setSuccess(`Resolved waiting-list entry for ${row.patient_name}.`);
                            await load();
                          } catch (err) {
                            setError(formatError(err, "Unable to resolve"));
                          }
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
      {open && can(user, "waitlist:write") ? (
        <Modal title="Add to waiting list" onClose={() => setOpen(false)}>
          <form onSubmit={add} className="form-grid">
            <Field label="Patient">
              <PatientPicker value={patientId} onChange={setPatientId} availableFor="waitlist" />
            </Field>
            <Field label="Added date">
              <input type="date" value={addedDate} onChange={(e) => setAddedDate(e.target.value)} />
            </Field>
            <Field label="Remarks">
              <textarea value={remarks} onChange={(e) => setRemarks(e.target.value)} />
            </Field>
            <button className="btn" disabled={saving}>{saving ? "Adding…" : "Add"}</button>
          </form>
        </Modal>
      ) : null}
      {checkInEntry && can(user, "stays:check_in") ? (
        <Modal title={`Check in · ${checkInEntry.patient_name}`} onClose={() => setCheckInEntry(null)}>
          <form className="form-grid" onSubmit={submitWaitlistCheckIn}>
            <Field label="Vacant room">
              <select required value={checkInRoomId} onChange={(e) => setCheckInRoomId(e.target.value)}>
                <option value="">{vacantRooms.length ? "Select a vacant room" : "No vacant rooms"}</option>
                {vacantRooms.map((room) => (
                  <option key={room.id} value={room.id}>Room {room.room_number}</option>
                ))}
              </select>
            </Field>
            <Field label="Check-in date">
              <input type="date" required value={checkInDate} onChange={(e) => setCheckInDate(e.target.value)} />
            </Field>
            <Field label="Room inspected">
              <select value={inspected ? "yes" : "no"} onChange={(e) => setInspected(e.target.value === "yes")}>
                <option value="no">No</option>
                <option value="yes">Yes</option>
              </select>
            </Field>
            <Field label="Remarks">
              <textarea value={checkInRemarks} onChange={(e) => setCheckInRemarks(e.target.value)} />
            </Field>
            <button className="btn" disabled={saving || !vacantRooms.length}>
              {saving ? "Checking in…" : "Confirm check-in"}
            </button>
          </form>
        </Modal>
      ) : null}
    </AppShell>
  );
}
