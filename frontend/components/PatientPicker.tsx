"use client";

import { useEffect, useState } from "react";
import { api, qs } from "@/lib/api";
import type { Page, PatientList } from "@/lib/types";

export function PatientPicker({
  value,
  onChange,
  id,
}: {
  value: string;
  onChange: (id: string) => void;
  id?: string;
}) {
  const [q, setQ] = useState("");
  const [items, setItems] = useState<PatientList[]>([]);
  const [selected, setSelected] = useState<PatientList | null>(null);

  useEffect(() => {
    const handle = setTimeout(() => {
      api<Page<PatientList>>(`/api/patients${qs({ q, page_size: 50 })}`)
        .then((page) => setItems(page.items))
        .catch(() => setItems([]));
    }, 200);
    return () => clearTimeout(handle);
  }, [q]);

  useEffect(() => {
    const found = items.find((patient) => String(patient.id) === value);
    if (found) {
      setSelected(found);
      return;
    }
    if (!value) {
      setSelected(null);
      return;
    }
    let cancelled = false;
    api<PatientList>(`/api/patients/${value}`)
      .then((patient) => {
        if (!cancelled) setSelected(patient);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [items, value]);

  const options =
    selected && !items.some((patient) => patient.id === selected.id) ? [selected, ...items] : items;

  return (
    <div className="form-grid" style={{ gridTemplateColumns: "1fr" }}>
      <input
        aria-label="Search patient"
        placeholder="Search name or registration no."
        value={q}
        onChange={(event) => setQ(event.target.value)}
      />
      <select
        id={id}
        required
        value={value}
        onChange={(event) => onChange(event.target.value)}
        aria-label="Select patient"
      >
        <option value="">Select patient</option>
        {options.map((patient) => (
          <option key={patient.id} value={patient.id}>
            {patient.name} ({patient.registration_no})
          </option>
        ))}
      </select>
    </div>
  );
}
