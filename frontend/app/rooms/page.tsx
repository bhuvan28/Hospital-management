"use client";

import { FormEvent, useEffect, useState } from "react";
import { AppShell, can, useUser } from "@/components/AppShell";
import { PatientPicker } from "@/components/PatientPicker";
import { Banner, Field, Modal, PageHeader } from "@/components/ui";
import { api, HttpError } from "@/lib/api";
import type { OccupancySummary, Room } from "@/lib/types";

export default function RoomsPage() {
  const user = useUser();
  const [rooms, setRooms] = useState<Room[]>([]);
  const [summary, setSummary] = useState<OccupancySummary | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [checkInRoom, setCheckInRoom] = useState<Room | null>(null);
  const [patientId, setPatientId] = useState("");
  const [inspected, setInspected] = useState(false);
  const [remarks, setRemarks] = useState("");
  const [admissionDate, setAdmissionDate] = useState("");
  const [loading, setLoading] = useState(true);

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
    setInspected(false);
    setRemarks("");
    setAdmissionDate("");
  }

  async function submitCheckIn(event: FormEvent) {
    event.preventDefault();
    if (!checkInRoom) return;
    try {
      await api(`/api/rooms/${checkInRoom.id}/check-in`, {
        method: "POST",
        body: JSON.stringify({
          patient_id: Number(patientId),
          room_inspected: inspected,
          remarks,
          hospital_admission_date: admissionDate || null,
        }),
      });
      setSuccess(`Checked in to room ${checkInRoom.room_number}.`);
      setCheckInRoom(null);
      await load();
    } catch (err) {
      setError(err instanceof HttpError ? err.message : "Check-in failed");
    }
  }

  async function checkout(room: Room) {
    if (!room.current_occupant) return;
    if (!window.confirm(`Check out ${room.current_occupant.patient_name} from room ${room.room_number}?`)) return;
    try {
      await api(`/api/stays/${room.current_occupant.stay_id}/check-out`, { method: "POST", body: JSON.stringify({}) });
      setSuccess(`Checked out of room ${room.room_number}.`);
      await load();
    } catch (err) {
      setError(err instanceof HttpError ? err.message : "Check-out failed");
    }
  }

  async function setMaintenance(room: Room, maintenance: boolean) {
    try {
      await api(`/api/rooms/${room.id}`, {
        method: "PATCH",
        body: JSON.stringify({ status: maintenance ? "maintenance" : "vacant" }),
      });
      await load();
    } catch (err) {
      setError(err instanceof HttpError ? err.message : "Unable to update room");
    }
  }

  return (
    <AppShell>
      <PageHeader
        title="Room board"
        subtitle="Live occupancy. Check-in is allowed only when a room is vacant."
      />
      {error ? <Banner kind="error">{error}</Banner> : null}
      {success ? <Banner kind="success">{success}</Banner> : null}
      {summary ? (
        <p className="muted">
          Occupancy {summary.occupancy_rate}% · {summary.occupied_rooms} occupied · {summary.vacant_rooms} vacant ·{" "}
          {summary.todays_check_ins} check-ins today
        </p>
      ) : null}
      {loading && !rooms.length ? <p className="muted">Loading room board…</p> : null}
      <div className="room-board">
        {rooms.map((room) => (
          <article key={room.id} className={`card room-card ${room.status}`}>
            <div className="topbar">
              <h2>Room {room.room_number}</h2>
              <span className={`badge ${room.status}`}>{room.status}</span>
            </div>
            {room.current_occupant ? (
              <>
                <div><strong>{room.current_occupant.patient_name}</strong></div>
                <div className="muted">{room.current_occupant.registration_no}</div>
                <div>In: {room.current_occupant.check_in_date}</div>
                <div>Ward: {room.current_occupant.ward_name || "—"}</div>
                <div>Officer: {room.current_occupant.officer_name || "—"}</div>
                <div>Inspected: {room.current_occupant.room_inspected ? "Yes" : "No"}</div>
                <div>{room.current_occupant.remarks}</div>
              </>
            ) : (
              <p className="muted">No current occupant.</p>
            )}
            <div className="room-actions">
              {can(user, "stays:check_in") && room.status === "vacant" ? (
                <button className="btn" type="button" onClick={() => openCheckIn(room)}>
                  Check in
                </button>
              ) : null}
              {can(user, "stays:check_out") && room.current_occupant ? (
                <button className="btn danger" type="button" onClick={() => checkout(room)}>
                  Check out
                </button>
              ) : null}
              {can(user, "rooms:write") && room.status !== "occupied" ? (
                <button className="btn secondary" type="button" onClick={() => setMaintenance(room, room.status !== "maintenance")}>
                  {room.status === "maintenance" ? "Mark vacant" : "Mark maintenance"}
                </button>
              ) : null}
            </div>
          </article>
        ))}
      </div>
      {checkInRoom ? (
        <Modal title={`Check in · Room ${checkInRoom.room_number}`} onClose={() => setCheckInRoom(null)}>
          <form onSubmit={submitCheckIn} className="form-grid">
            <Field label="Patient">
              <PatientPicker value={patientId} onChange={setPatientId} />
            </Field>
            <Field label="Hospital admission date">
              <input type="date" value={admissionDate} onChange={(e) => setAdmissionDate(e.target.value)} />
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
            <button className="btn">Confirm check-in</button>
          </form>
        </Modal>
      ) : null}
    </AppShell>
  );
}
