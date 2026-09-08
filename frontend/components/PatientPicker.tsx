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

  useEffect(() => {
    const handle = setTimeout(() => {
      api<Page<PatientList>>(`/api/patients${qs({ q, page_size: 50 })}`)
        .then((page) => setItems(page.items))
        .catch(() => setItems([]));
    }, 200);
    return () => clearTimeout(handle);
  }, [q]);

  return (
    <div className="form-grid" style={{ gridTemplateColumns: "1fr" }}>
      <input
        aria-label="Search patient"
        placeholder="Search name or registration no."
        value={q}
        onChange={(event) => setQ(event.target.value)}
      />
      <select id={id} required value={value} onChange={(event) => onChange(event.target.value)} aria-label="Select patient">
        <option value="">Select patient</option>
        {items.map((patient) => (
          <option key={patient.id} value={patient.id}>
            {patient.name} ({patient.registration_no})
          </option>
        ))}
      </select>
    </div>
  );
}
