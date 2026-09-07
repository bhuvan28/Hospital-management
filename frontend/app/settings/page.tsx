"use client";

import { FormEvent, useEffect, useState } from "react";
import { AppShell, can, useUser } from "@/components/AppShell";
import { Banner, Empty, Field, PageHeader } from "@/components/ui";
import { api, HttpError } from "@/lib/api";
import type { Lookup, Room } from "@/lib/types";

function LookupManager({ title, path }: { title: string; path: string }) {
  const [rows, setRows] = useState<Lookup[]>([]);
  const [name, setName] = useState("");
  const [error, setError] = useState("");

  async function load() {
    setRows(await api<Lookup[]>(path));
  }

  useEffect(() => {
    load().catch((err) => setError(err.message));
  }, [path]);

  async function add(event: FormEvent) {
    event.preventDefault();
    try {
      await api(path, { method: "POST", body: JSON.stringify({ name, active: true }) });
      setName("");
      await load();
    } catch (err) {
      setError(err instanceof HttpError ? err.message : "Unable to add");
    }
  }

  return (
    <div className="card">
      <h2>{title}</h2>
      {error ? <Banner kind="error">{error}</Banner> : null}
      <form onSubmit={add} className="toolbar">
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder={`New ${title.toLowerCase()}`} required style={{ maxWidth: 260 }} />
        <button className="btn">Add</button>
      </form>
      {!rows.length ? <Empty>No {title.toLowerCase()} yet.</Empty> : (
        <table>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id}>
                <td>{row.name}</td>
                <td>{row.active ? "Active" : "Inactive"}</td>
                <td>
                  <button
                    className="btn secondary"
                    onClick={async () => {
                      if (!window.confirm(`${row.active ? "Deactivate" : "Activate"} ${row.name}?`)) return;
                      await api(`${path}/${row.id}`, { method: "PATCH", body: JSON.stringify({ active: !row.active }) });
                      await load();
                    }}
                  >
                    {row.active ? "Deactivate" : "Activate"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default function SettingsPage() {
  const user = useUser();
  if (!can(user, "settings:manage")) {
    return (
      <AppShell>
        <Banner kind="error">Settings are limited to administrators.</Banner>
      </AppShell>
    );
  }
  return (
    <AppShell>
      <PageHeader title="Settings" subtitle="Rooms, wards, states and donation categories are lookup tables — not hardcoded enums." />
      <RoomManager />
      <div className="grid" style={{ marginTop: 16, gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))" }}>
        <LookupManager title="Wards / clinics" path="/api/lookups/wards" />
        <LookupManager title="States / regions" path="/api/lookups/states" />
        <LookupManager title="Donation categories" path="/api/lookups/donation-categories" />
      </div>
    </AppShell>
  );
}

function RoomManager() {
  const [rooms, setRooms] = useState<Room[]>([]);
  const [number, setNumber] = useState("");
  const [renames, setRenames] = useState<Record<number, string>>({});
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function load() {
    const next = await api<Room[]>("/api/rooms");
    setRooms(next);
    setRenames(Object.fromEntries(next.map((room) => [room.id, room.room_number])));
  }

  useEffect(() => {
    load().catch((err) => setError(err.message));
  }, []);

  async function add(event: FormEvent) {
    event.preventDefault();
    try {
      await api("/api/rooms", { method: "POST", body: JSON.stringify({ room_number: number }) });
      setNumber("");
      setMessage("Room added.");
      await load();
    } catch (err) {
      setError(err instanceof HttpError ? err.message : "Unable to add room");
    }
  }

  return (
    <div className="card">
      <h2>Rooms</h2>
      <p className="muted">The house is seeded with 18 rooms. Add, rename or remove unused rooms here; do not hardcode the count in the UI.</p>
      {error ? <Banner kind="error">{error}</Banner> : null}
      {message ? <Banner kind="success">{message}</Banner> : null}
      <form onSubmit={add} className="toolbar">
        <Field label="Room number">
          <input value={number} onChange={(e) => setNumber(e.target.value)} required />
        </Field>
        <button className="btn" style={{ alignSelf: "end" }}>Add room</button>
      </form>
      <div className="table-wrap" style={{ marginTop: 12 }}>
        {!rooms.length ? <Empty>No rooms configured.</Empty> : (
          <table>
            <thead>
              <tr><th>Number</th><th>Status</th><th>Occupant</th><th></th></tr>
            </thead>
            <tbody>
              {rooms.map((room) => (
                <tr key={room.id}>
                  <td>
                    <input
                      aria-label={`Rename room ${room.room_number}`}
                      value={renames[room.id] ?? room.room_number}
                      onChange={(e) => setRenames({ ...renames, [room.id]: e.target.value })}
                      style={{ maxWidth: 120 }}
                    />
                  </td>
                  <td><span className={`badge ${room.status}`}>{room.status}</span></td>
                  <td>{room.current_occupant?.patient_name || "—"}</td>
                  <td>
                    <button
                      className="btn secondary"
                      type="button"
                      onClick={async () => {
                        try {
                          await api(`/api/rooms/${room.id}`, { method: "PATCH", body: JSON.stringify({ room_number: renames[room.id] }) });
                          setMessage(`Room ${room.room_number} renamed.`);
                          await load();
                        } catch (err) {
                          setError(err instanceof HttpError ? err.message : "Unable to rename room");
                        }
                      }}
                    >
                      Save name
                    </button>
                    {!room.current_occupant ? (
                      <button
                        className="btn danger"
                        type="button"
                        style={{ marginLeft: 8 }}
                        onClick={async () => {
                          if (!window.confirm(`Delete room ${room.room_number}? Rooms with stay history cannot be deleted.`)) return;
                          try {
                            await api(`/api/rooms/${room.id}`, { method: "DELETE" });
                            setMessage(`Room ${room.room_number} deleted.`);
                            await load();
                          } catch (err) {
                            setError(err instanceof HttpError ? err.message : "Unable to delete room");
                          }
                        }}
                      >
                        Delete
                      </button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
