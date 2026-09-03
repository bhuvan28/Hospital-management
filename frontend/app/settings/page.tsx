"use client";

import { FormEvent, useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { Banner, Field, PageHeader } from "@/components/ui";
import { api, HttpError } from "@/lib/api";
import type { Lookup } from "@/lib/types";

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
                    await api(`${path}/${row.id}`, { method: "PATCH", body: JSON.stringify({ active: !row.active }) });
                    await load();
                  }}
                >
                  Toggle
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function SettingsPage() {
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
  const [number, setNumber] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function add(event: FormEvent) {
    event.preventDefault();
    try {
      await api("/api/rooms", { method: "POST", body: JSON.stringify({ room_number: number }) });
      setNumber("");
      setMessage("Room added. Open the Rooms board to see it.");
    } catch (err) {
      setError(err instanceof HttpError ? err.message : "Unable to add room");
    }
  }

  return (
    <div className="card">
      <h2>Rooms</h2>
      <p className="muted">The house is seeded with 18 rooms. Add or rename rooms here; do not hardcode the count in the UI.</p>
      {error ? <Banner kind="error">{error}</Banner> : null}
      {message ? <Banner kind="success">{message}</Banner> : null}
      <form onSubmit={add} className="toolbar">
        <Field label="Room number">
          <input value={number} onChange={(e) => setNumber(e.target.value)} required />
        </Field>
        <button className="btn" style={{ alignSelf: "end" }}>Add room</button>
      </form>
    </div>
  );
}
