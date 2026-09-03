"use client";

import { FormEvent, useEffect, useState } from "react";
import { AppShell, can, useUser } from "@/components/AppShell";
import { Banner, Empty, Field, Modal, PageHeader } from "@/components/ui";
import { api, HttpError, qs } from "@/lib/api";
import type { Lookup, Page, PatientDetail, PatientList } from "@/lib/types";

const emptyForm = {
  name: "",
  registration_no: "",
  nric: "",
  gender: "female",
  dob: "",
  address: "",
  diagnosis: "",
  referring_doctor: "",
  ward_clinic_id: "",
  state_id: "",
  status: "new",
  registered_online: false,
  sibling_count: 0,
  sibling_names: "",
  guardian_name: "",
  guardian_relationship: "Mother",
  guardian_contact: "",
  assessment_notes: "",
  assessed_fee_amount: "",
};

export default function PatientsPage() {
  const user = useUser();
  const [rows, setRows] = useState<Page<PatientList> | null>(null);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [ward, setWard] = useState("");
  const [wards, setWards] = useState<Lookup[]>([]);
  const [states, setStates] = useState<Lookup[]>([]);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [form, setForm] = useState(emptyForm);
  const [open, setOpen] = useState(false);
  const [detail, setDetail] = useState<PatientDetail | null>(null);
  const [page, setPage] = useState(1);

  const canWrite = can(user, "patients:write");

  async function load() {
    const data = await api<Page<PatientList>>(
      `/api/patients${qs({ q, status, ward_clinic_id: ward || undefined, page })}`,
    );
    setRows(data);
  }

  useEffect(() => {
    api<Lookup[]>("/api/lookups/wards").then(setWards).catch(() => undefined);
    api<Lookup[]>("/api/lookups/states").then(setStates).catch(() => undefined);
  }, []);

  useEffect(() => {
    load().catch((err) => setError(err.message));
  }, [q, status, ward, page]);

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await api("/api/patients", {
        method: "POST",
        body: JSON.stringify({
          ...form,
          ward_clinic_id: Number(form.ward_clinic_id),
          state_id: Number(form.state_id),
          sibling_count: Number(form.sibling_count),
          assessed_fee_amount: form.assessed_fee_amount || null,
          guardians: form.guardian_name
            ? [{ name: form.guardian_name, relationship: form.guardian_relationship, contact: form.guardian_contact }]
            : [],
          assessment: {
            payload: {},
            notes: form.assessment_notes || null,
            assessed_fee_amount: form.assessed_fee_amount || null,
          },
        }),
      });
      setSuccess("Patient intake saved.");
      setOpen(false);
      setForm(emptyForm);
      await load();
    } catch (err) {
      setError(err instanceof HttpError ? err.message : "Unable to save");
    }
  }

  return (
    <AppShell>
      <PageHeader
        title="Patients"
        subtitle="Family intake for RMH HCTM UKM. NRIC and diagnosis are hidden from unauthorised roles."
        actions={
          canWrite ? (
            <button className="btn" onClick={() => setOpen(true)}>
              New intake
            </button>
          ) : null
        }
      />
      {error ? <Banner kind="error">{error}</Banner> : null}
      {success ? <Banner kind="success">{success}</Banner> : null}
      <div className="toolbar">
        <input placeholder="Search name or registration no." value={q} onChange={(e) => setQ(e.target.value)} style={{ maxWidth: 280 }} />
        <select value={status} onChange={(e) => setStatus(e.target.value)} style={{ maxWidth: 180 }}>
          <option value="">All statuses</option>
          <option value="new">New</option>
          <option value="returning">Returning</option>
        </select>
        <select value={ward} onChange={(e) => setWard(e.target.value)} style={{ maxWidth: 240 }}>
          <option value="">All wards</option>
          {wards.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>
      </div>
      <div className="card table-wrap">
        {!rows?.items.length ? (
          <Empty>No patient records match the current filters.</Empty>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Registration</th>
                <th>Ward</th>
                <th>State</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rows.items.map((row) => (
                <tr key={row.id}>
                  <td>{row.name}</td>
                  <td>{row.registration_no}</td>
                  <td>{row.ward_clinic.name}</td>
                  <td>{row.state.name}</td>
                  <td>
                    <span className={`badge ${row.status}`}>{row.status}</span>
                  </td>
                  <td>
                    <button
                      className="btn secondary"
                      onClick={async () => setDetail(await api<PatientDetail>(`/api/patients/${row.id}`))}
                    >
                      View
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div className="pagination">
          <button className="btn secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            Previous
          </button>
          <span>
            Page {rows?.page ?? 1} of {rows?.pages || 1}
          </span>
          <button className="btn secondary" disabled={(rows?.page ?? 1) >= (rows?.pages || 1)} onClick={() => setPage((p) => p + 1)}>
            Next
          </button>
        </div>
      </div>

      {open ? (
        <Modal title="Patient intake" onClose={() => setOpen(false)}>
          <form className="form-grid" onSubmit={onCreate}>
            <Field label="Patient full name">
              <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </Field>
            <Field label="Registration number">
              <input required placeholder="HCTM26-0001" value={form.registration_no} onChange={(e) => setForm({ ...form, registration_no: e.target.value })} />
            </Field>
            <Field label="NRIC / identification">
              <input required value={form.nric} onChange={(e) => setForm({ ...form, nric: e.target.value })} />
            </Field>
            <Field label="Gender">
              <select value={form.gender} onChange={(e) => setForm({ ...form, gender: e.target.value })}>
                <option value="female">Female</option>
                <option value="male">Male</option>
                <option value="other">Other</option>
                <option value="unspecified">Unspecified</option>
              </select>
            </Field>
            <Field label="Date of birth">
              <input type="date" required value={form.dob} onChange={(e) => setForm({ ...form, dob: e.target.value })} />
            </Field>
            <Field label="Ward / Clinic">
              <select required value={form.ward_clinic_id} onChange={(e) => setForm({ ...form, ward_clinic_id: e.target.value })}>
                <option value="">Select</option>
                {wards.filter((w) => w.active).map((item) => (
                  <option key={item.id} value={item.id}>{item.name}</option>
                ))}
              </select>
            </Field>
            <Field label="State / region">
              <select required value={form.state_id} onChange={(e) => setForm({ ...form, state_id: e.target.value })}>
                <option value="">Select</option>
                {states.filter((s) => s.active).map((item) => (
                  <option key={item.id} value={item.id}>{item.name}</option>
                ))}
              </select>
            </Field>
            <Field label="Status">
              <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
                <option value="new">New</option>
                <option value="returning">Returning</option>
              </select>
            </Field>
            <Field label="Referring doctor">
              <input value={form.referring_doctor} onChange={(e) => setForm({ ...form, referring_doctor: e.target.value })} />
            </Field>
            <Field label="Address">
              <textarea required value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
            </Field>
            <Field label="Diagnosis">
              <textarea required value={form.diagnosis} onChange={(e) => setForm({ ...form, diagnosis: e.target.value })} />
            </Field>
            <Field label="Sibling names">
              <input value={form.sibling_names} onChange={(e) => setForm({ ...form, sibling_names: e.target.value })} />
            </Field>
            <Field label="Sibling count">
              <input type="number" min={0} value={form.sibling_count} onChange={(e) => setForm({ ...form, sibling_count: Number(e.target.value) })} />
            </Field>
            <Field label="Guardian name">
              <input value={form.guardian_name} onChange={(e) => setForm({ ...form, guardian_name: e.target.value })} />
            </Field>
            <Field label="Guardian relationship">
              <input value={form.guardian_relationship} onChange={(e) => setForm({ ...form, guardian_relationship: e.target.value })} />
            </Field>
            <Field label="Guardian contact">
              <input value={form.guardian_contact} onChange={(e) => setForm({ ...form, guardian_contact: e.target.value })} />
            </Field>
            <div className="sensitive" style={{ gridColumn: "1 / -1" }}>
              <strong>Social worker assessment</strong>
              <p className="muted">Exact room-fee fields are not yet confirmed in the PRD. Capture notes and an optional assessed amount only.</p>
              <Field label="Assessment notes">
                <textarea value={form.assessment_notes} onChange={(e) => setForm({ ...form, assessment_notes: e.target.value })} />
              </Field>
              <Field label="Optional assessed fee (RM)">
                <input type="number" min={0} step="0.01" value={form.assessed_fee_amount} onChange={(e) => setForm({ ...form, assessed_fee_amount: e.target.value })} />
              </Field>
            </div>
            <button className="btn" type="submit">Save intake</button>
          </form>
        </Modal>
      ) : null}

      {detail ? (
        <Modal title={detail.name} onClose={() => setDetail(null)}>
          <p>
            <strong>{detail.registration_no}</strong> · {detail.ward_clinic.name} · {detail.state.name}
          </p>
          {detail.nric ? <p>NRIC: {detail.nric}</p> : <p className="muted">Sensitive identity fields are hidden for this role.</p>}
          {detail.diagnosis ? <p>Diagnosis: {detail.diagnosis}</p> : null}
          {detail.address ? <p>Address: {detail.address}</p> : null}
          {detail.guardians?.map((g) => (
            <p key={g.name}>
              Guardian: {g.name} ({g.relationship}) {g.contact}
            </p>
          ))}
        </Modal>
      ) : null}
    </AppShell>
  );
}
