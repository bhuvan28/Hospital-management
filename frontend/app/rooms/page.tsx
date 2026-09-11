"use client";

import { FormEvent, useEffect, useState } from "react";
import { AppShell, can, useUser } from "@/components/AppShell";
import { PatientPicker } from "@/components/PatientPicker";
import { Banner, Empty, Field, Loading, Modal, PageHeader } from "@/components/ui";
import { api, HttpError } from "@/lib/api";
import { occupancyStatus, type OccupancySummary, type Room, type Stay } from "@/lib/types";

export default function RoomsPage() {
  const user = useUser();
  const [rooms, setRooms] = useState<Room[]>([]);
  const [summary, setSummary] = useState<OccupancySummary | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [checkInRoom, setCheckInRoom] = useState<Room | null>(null);
  const [checkoutRoom, setCheckoutRoom] = useState<Room | null>(null);
  const [historyRoom, setHistoryRoom] = useState<Room | null>(null);
  const [history, setHistory] = useState<Stay[]>([]);
  const [patientId, setPatientId] = useState("");
  const [inspected, setInspected] = useState(false);
  const [remarks, setRemarks] = useState("");
  const [admissionDate, setAdmissionDate] = useState("");
  const [checkInDate, setCheckInDate] = useState("");
  const [checkoutDate, setCheckoutDate] = useState("");
  const [checkoutRemarks, setCheckoutRemarks] = useState("");
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadingHistory, setLoadingHistory] = useState(false);

  async function load() {
    const [board, occupancy] = await Promise.all([
      api<Room[]>("/api/rooms"),
      api<OccupancySummary>("/api/occupancy/summary"),
    ]);
    setRooms(board);
    setSummary(occupancy);
    setLoading(false);
  }

  useEffect(() => {
    load().catch((err) => {
      setError(err.message);
      setLoading(false);
    });
  }, []);

  async function openCheckIn(room: Room) {
    setCheckInRoom(room);
    setPatientId("");
    setCheckInDate(new Date().toISOString().slice(0, 10));
    setInspected(false);
    setRemarks("");
    setAdmissionDate("");
  }

  async function submitCheckIn(event: FormEvent) {
    event.preventDefault();
    if (!checkInRoom) return;
    setSaving(true);
    setError("");
    try {
      await api(`/api/rooms/${checkInRoom.id}/check-in`, {
        method: "POST",
        body: JSON.stringify({
          patient_id: Number(patientId),
          room_inspected: inspected,
          remarks,
          hospital_admission_date: admissionDate || null,
          check_in_date: checkInDate || null,
        }),
      });
      setSuccess(`Checked in to room ${checkInRoom.room_number}.`);
      setCheckInRoom(null);
      await load();
    } catch (err) {
      setError(err instanceof HttpError ? err.message : "Check-in failed");
    } finally {
      setSaving(false);
    }
  }

  function openCheckout(room: Room) {
    if (!room.current_occupant) return;
    setCheckoutRoom(room);
    setCheckoutDate(new Date().toISOString().slice(0, 10));
    setCheckoutRemarks(room.current_occupant.remarks || "");
  }

  async function submitCheckout(event: FormEvent) {
    event.preventDefault();
    if (!checkoutRoom?.current_occupant) return;
    setSaving(true);
    setError("");
    try {
      await api(`/api/stays/${checkoutRoom.current_occupant.stay_id}/check-out`, {
        method: "POST",
        body: JSON.stringify({
          check_out_date: checkoutDate || null,
          remarks: checkoutRemarks || null,
        }),
      });
      setSuccess(`Checked out of room ${checkoutRoom.room_number}.`);
      setCheckoutRoom(null);
      await load();
    } catch (err) {
      setError(err instanceof HttpError ? err.message : "Check-out failed");
    } finally {
      setSaving(false);
    }
  }

  async function openHistory(room: Room) {
    setHistoryRoom(room);
    setLoadingHistory(true);
    try {
      setHistory(await api<Stay[]>(`/api/stays?room_id=${room.id}`));
    } catch (err) {
      setError(err instanceof HttpError ? err.message : "Unable to load stay history");
      setHistory([]);
    } finally {
      setLoadingHistory(false);
    }
  }

  async function setMaintenance(room: Room, maintenance: boolean) {
    const next = maintenance ? "maintenance" : "vacant";
    if (!window.confirm(`Mark room ${room.room_number} as ${next}?`)) return;
    try {
      await api(`/api/rooms/${room.id}`, {
        method: "PATCH",
        body: JSON.stringify({ status: next }),
      });
      setSuccess(`Room ${room.room_number} is now ${next}.`);
      await load();
    } catch (err) {
      setError(err instanceof HttpError ? err.message : "Unable to update room");
    }
  }

  return (
    <AppShell>
      <PageHeader
        title="Room board"
        subtitle="Live occupancy. Check-in follows the current occupant and is blocked while a room is in maintenance."
      />
      {error ? <Banner kind="error">{error}</Banner> : null}
      {success ? <Banner kind="success">{success}</Banner> : null}
      {summary ? (
        <p className="muted">
          Occupancy {summary.occupancy_rate}% · {summary.occupied_rooms} occupied · {summary.vacant_rooms} vacant ·{" "}
          {summary.todays_check_ins} check-ins today · {summary.todays_check_outs} check-outs today
        </p>
      ) : null}
      {loading && !rooms.length ? <Loading>Loading room board…</Loading> : null}
      {!loading && !rooms.length ? <Empty>No rooms are configured yet. Add rooms in Settings.</Empty> : null}
      <div className="room-board">
        {rooms.map((room) => {
          const liveStatus = occupancyStatus(room);
          return (
          <article key={room.id} className={`card room-card ${liveStatus}`}>
            <div className="topbar">
              <h2>Room {room.room_number}</h2>
              <span className={`badge ${liveStatus}`}>{liveStatus}</span>
            </div>
            {room.current_occupant ? (
              <>
                <div><strong>{room.current_occupant.patient_name}</strong></div>
                <div className="muted">{room.current_occupant.registration_no}</div>
                <div>In: {room.current_occupant.check_in_date}</div>
                <div>Ward: {room.current_occupant.ward_name || "—"}</div>
                <div>Officer: {room.current_occupant.officer_name || "—"}</div>
                <div>Inspected: {room.current_occupant.room_inspected ? "Yes" : "No"}</div>
                {room.current_occupant.remarks ? <div>{room.current_occupant.remarks}</div> : null}
              </>
            ) : (
              <p className="muted">No current occupant.</p>
            )}
            {room.notes ? <p className="muted">{room.notes}</p> : null}
            <div className="room-actions">
              {can(user, "stays:check_in") && !room.current_occupant && liveStatus !== "maintenance" ? (
                <button className="btn" type="button" onClick={() => openCheckIn(room)}>
                  Check in
                </button>
              ) : null}
              {can(user, "stays:check_out") && room.current_occupant ? (
                <button className="btn danger" type="button" onClick={() => openCheckout(room)}>
                  Check out
                </button>
              ) : null}
              <button className="btn secondary" type="button" onClick={() => openHistory(room)}>
                Stay history
              </button>
              {can(user, "rooms:write") && !room.current_occupant ? (
                <button className="btn secondary" type="button" onClick={() => setMaintenance(room, liveStatus !== "maintenance")}>
                  {liveStatus === "maintenance" ? "Mark vacant" : "Mark maintenance"}
                </button>
              ) : null}
            </div>
          </article>
          );
        })}
      </div>
      {rooms.length ? (
        <div className="card table-wrap" style={{ marginTop: 16 }}>
          <table>
            <caption className="muted" style={{ textAlign: "left", captionSide: "top", marginBottom: 8 }}>
              Occupancy board (status follows the current occupant, not a stale flag)
            </caption>
            <thead>
              <tr>
                <th>Room</th>
                <th>Status</th>
                <th>Patient</th>
                <th>Registration</th>
                <th>Check-in</th>
                <th>Ward</th>
                <th>Officer</th>
                <th>Inspected</th>
                <th>Remarks</th>
              </tr>
            </thead>
            <tbody>
              {rooms.map((room) => {
                const liveStatus = occupancyStatus(room);
                return (
                  <tr key={`row-${room.id}`}>
                    <td>{room.room_number}</td>
                    <td><span className={`badge ${liveStatus}`}>{liveStatus}</span></td>
                    <td>{room.current_occupant?.patient_name || "—"}</td>
                    <td>{room.current_occupant?.registration_no || "—"}</td>
                    <td>{room.current_occupant?.check_in_date || "—"}</td>
                    <td>{room.current_occupant?.ward_name || "—"}</td>
                    <td>{room.current_occupant?.officer_name || "—"}</td>
                    <td>{room.current_occupant ? (room.current_occupant.room_inspected ? "Yes" : "No") : "—"}</td>
                    <td>{room.current_occupant?.remarks || room.notes || "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : null}
      {checkInRoom ? (
        <Modal title={`Check in · Room ${checkInRoom.room_number}`} onClose={() => setCheckInRoom(null)}>
          <form onSubmit={submitCheckIn} className="form-grid">
            <Field label="Patient">
              <PatientPicker value={patientId} onChange={setPatientId} />
            </Field>
            <Field label="Hospital admission date">
              <input type="date" value={admissionDate} onChange={(e) => setAdmissionDate(e.target.value)} />
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
              <textarea value={remarks} onChange={(e) => setRemarks(e.target.value)} />
            </Field>
            <button className="btn" disabled={saving}>{saving ? "Checking in…" : "Confirm check-in"}</button>
          </form>
        </Modal>
      ) : null}
      {checkoutRoom?.current_occupant ? (
        <Modal title={`Check out · Room ${checkoutRoom.room_number}`} onClose={() => setCheckoutRoom(null)}>
          <p>
            {checkoutRoom.current_occupant.patient_name} ({checkoutRoom.current_occupant.registration_no}) checked in{" "}
            {checkoutRoom.current_occupant.check_in_date}.
          </p>
          <form onSubmit={submitCheckout} className="form-grid">
            <Field label="Check-out date" hint="Cannot be before the check-in date.">
              <input
                type="date"
                required
                min={checkoutRoom.current_occupant.check_in_date}
                value={checkoutDate}
                onChange={(e) => setCheckoutDate(e.target.value)}
              />
            </Field>
            <Field label="Remarks">
              <textarea value={checkoutRemarks} onChange={(e) => setCheckoutRemarks(e.target.value)} />
            </Field>
            <button className="btn danger" disabled={saving}>{saving ? "Checking out…" : "Confirm check-out"}</button>
          </form>
        </Modal>
      ) : null}
      {historyRoom ? (
        <Modal title={`Stay history · Room ${historyRoom.room_number}`} onClose={() => setHistoryRoom(null)}>
          {loadingHistory ? <Loading>Loading stay history…</Loading> : null}
          {!loadingHistory && !history.length ? <Empty>No stays recorded for this room.</Empty> : null}
          {history.length ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Patient</th>
                    <th>Registration</th>
                    <th>Check-in</th>
                    <th>Check-out</th>
                    <th>Officer</th>
                    <th>Inspected</th>
                    <th>Remarks</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((stay) => (
                    <tr key={stay.id}>
                      <td>{stay.patient_name || "—"}</td>
                      <td>{stay.registration_no || "—"}</td>
                      <td>{stay.check_in_date}</td>
                      <td>{stay.check_out_date || "In house"}</td>
                      <td>{stay.officer_name || "—"}</td>
                      <td>{stay.room_inspected ? "Yes" : "No"}</td>
                      <td>{stay.remarks || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </Modal>
      ) : null}
    </AppShell>
  );
}
