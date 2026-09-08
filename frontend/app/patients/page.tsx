"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { AppShell, can, useUser } from "@/components/AppShell";
import { Banner, Empty, Field, Loading, Modal, PageHeader } from "@/components/ui";
import { api, HttpError, qs } from "@/lib/api";
import type { Lookup, Page, PatientDetail, PatientList } from "@/lib/types";

type GuardianForm = { name: string; relationship: string; contact: string };

type IntakeForm = {
  name: string;
  registration_no: string;
  nric: string;
  gender: string;
  dob: string;
  address: string;
  diagnosis: string;
  referring_doctor: string;
  ward_clinic_id: string;
  state_id: string;
  status: string;
  registered_online: boolean;
  registered_at: string;
  sibling_count: number;
  sibling_names: string;
  guardians: GuardianForm[];
  assessment_notes: string;
  assessed_fee_amount: string;
  assessment_payload: Record<string, unknown>;
};

const emptyForm = (): IntakeForm => ({
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
  registered_at: new Date().toISOString().slice(0, 10),
  sibling_count: 0,
  sibling_names: "",
  guardians: [{ name: "", relationship: "Mother", contact: "" }],
  assessment_notes: "",
  assessed_fee_amount: "",
  assessment_payload: {},
});

function formFromDetail(detail: PatientDetail): IntakeForm {
  return {
    name: detail.name,
    registration_no: detail.registration_no,
    nric: detail.nric || "",
    gender: detail.gender,
    dob: detail.dob || "",
    address: detail.address || "",
    diagnosis: detail.diagnosis || "",
    referring_doctor: detail.referring_doctor || "",
    ward_clinic_id: String(detail.ward_clinic.id),
    state_id: String(detail.state.id),
    status: detail.status,
    registered_online: detail.registered_online,
    registered_at: detail.registered_at.slice(0, 10),
    sibling_count: detail.sibling_count,
    sibling_names: detail.sibling_names || "",
    guardians: detail.guardians.length
      ? detail.guardians.map((g) => ({ name: g.name, relationship: g.relationship, contact: g.contact }))
      : [{ name: "", relationship: "Mother", contact: "" }],
    assessment_notes: detail.assessment?.notes || "",
    assessed_fee_amount: detail.assessment?.assessed_fee_amount || "",
    assessment_payload: detail.assessment?.payload || {},
  };
}

export default function PatientsPage() {
  const user = useUser();
  const [rows, setRows] = useState<Page<PatientList> | null>(null);
  const [q, setQ] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [ward, setWard] = useState("");
  const [sortBy, setSortBy] = useState("name");
  const [sortDir, setSortDir] = useState("asc");
  const [wards, setWards] = useState<Lookup[]>([]);
  const [states, setStates] = useState<Lookup[]>([]);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [form, setForm] = useState<IntakeForm>(emptyForm);
  const [open, setOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [detail, setDetail] = useState<PatientDetail | null>(null);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  const canWrite = can(user, "patients:write");
  const canSensitive = can(user, "patients:read_sensitive");

  useEffect(() => {
    const handle = setTimeout(() => {
      setSearch(q);
      setPage(1);
    }, 300);
    return () => clearTimeout(handle);
  }, [q]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api<Page<PatientList>>(
        `/api/patients${qs({
          q: search,
          status,
          ward_clinic_id: ward || undefined,
          page,
          sort_by: sortBy,
          sort_dir: sortDir,
        })}`,
      );
      setRows(data);
      setError("");
    } finally {
      setLoading(false);
    }
  }, [search, status, ward, page, sortBy, sortDir]);

  useEffect(() => {
    api<Lookup[]>("/api/lookups/wards").then(setWards).catch(() => undefined);
    api<Lookup[]>("/api/lookups/states").then(setStates).catch(() => undefined);
  }, []);

  useEffect(() => {
    load().catch((err) => setError(err.message));
  }, [load]);

  function payloadFromForm() {
    return {
      name: form.name,
      registration_no: form.registration_no,
      nric: form.nric,
      gender: form.gender,
      dob: form.dob,
      address: form.address,
      diagnosis: form.diagnosis,
      referring_doctor: form.referring_doctor || null,
      ward_clinic_id: Number(form.ward_clinic_id),
      state_id: Number(form.state_id),
      status: form.status,
      registered_online: form.registered_online,
      registered_at: form.registered_at ? new Date(`${form.registered_at}T00:00:00Z`).toISOString() : undefined,
      sibling_count: Number(form.sibling_count),
      sibling_names: form.sibling_names || null,
      guardians: form.guardians.filter((g) => g.name.trim()),
      assessment: {
        payload: form.assessment_payload || {},
        notes: form.assessment_notes || null,
        assessed_fee_amount: form.assessed_fee_amount || null,
      },
    };
  }

  async function onSave(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      if (editingId) {
        await api(`/api/patients/${editingId}`, { method: "PATCH", body: JSON.stringify(payloadFromForm()) });
        setSuccess("Patient record updated.");
      } else {
        await api("/api/patients", { method: "POST", body: JSON.stringify(payloadFromForm()) });
        setSuccess("Patient intake saved.");
      }
      setOpen(false);
      setEditingId(null);
      setForm(emptyForm());
      await load();
    } catch (err) {
      setError(err instanceof HttpError ? err.message : "Unable to save");
    }
  }

  async function openEdit(id: number) {
    const record = await api<PatientDetail>(`/api/patients/${id}`);
    setForm(formFromDetail(record));
    setEditingId(id);
    setOpen(true);
  }

  const sortLabel = useMemo(() => `${sortBy}:${sortDir}`, [sortBy, sortDir]);

  function toggleSort(column: string) {
    if (sortBy === column) {
      setSortDir((dir) => (dir === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(column);
      setSortDir("asc");
    }
  }

  return (
    <AppShell>
      <PageHeader
        title="Patients"
        subtitle="Family intake for RMH HCTM UKM. NRIC, diagnosis and guardian details are hidden from unauthorised roles."
        actions={
          canWrite ? (
            <button
              className="btn"
              onClick={() => {
                setEditingId(null);
                setForm(emptyForm());
                setOpen(true);
              }}
            >
              New intake
            </button>
          ) : null
        }
      />
      {error ? <Banner kind="error">{error}</Banner> : null}
      {success ? <Banner kind="success">{success}</Banner> : null}
      <div className="toolbar">
        <input
          placeholder="Search name or registration no."
          value={q}
          onChange={(e) => setQ(e.target.value)}
          style={{ maxWidth: 280 }}
          aria-label="Search patients"
        />
        <select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }} style={{ maxWidth: 180 }} aria-label="Filter by status">
          <option value="">All statuses</option>
          <option value="new">New</option>
          <option value="returning">Returning</option>
        </select>
        <select value={ward} onChange={(e) => { setWard(e.target.value); setPage(1); }} style={{ maxWidth: 240 }} aria-label="Filter by ward">
          <option value="">All wards</option>
          {wards.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>
      </div>
      <div className="card table-wrap">
        {loading && !rows ? (
          <Loading>Loading patient records…</Loading>
        ) : !rows?.items.length ? (
          <Empty>No patient records match the current filters.</Empty>
        ) : (
          <table>
            <thead>
              <tr>
                <th>
                  <button type="button" className="linkish" onClick={() => toggleSort("name")}>
                    Name {sortLabel.startsWith("name") ? (sortDir === "asc" ? "↑" : "↓") : ""}
                  </button>
                </th>
                <th>
                  <button type="button" className="linkish" onClick={() => toggleSort("registration_no")}>
                    Registration
                  </button>
                </th>
                <th>Ward</th>
                <th>State</th>
                <th>
                  <button type="button" className="linkish" onClick={() => toggleSort("status")}>
                    Status
                  </button>
                </th>
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
                      onClick={async () => {
                        try {
                          setDetail(await api<PatientDetail>(`/api/patients/${row.id}`));
                        } catch (err) {
                          setError(err instanceof HttpError ? err.message : "Unable to load patient");
                        }
                      }}
                    >
                      View
                    </button>
                    {canWrite && canSensitive ? (
                      <button className="btn secondary" style={{ marginLeft: 8 }} onClick={() => openEdit(row.id)}>
                        Edit
                      </button>
                    ) : null}
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
            Page {rows?.page ?? 1} of {rows?.pages || 1} · {rows?.total ?? 0} families
          </span>
          <button className="btn secondary" disabled={(rows?.page ?? 1) >= (rows?.pages || 1)} onClick={() => setPage((p) => p + 1)}>
            Next
          </button>
        </div>
      </div>

      {open ? (
        <Modal title={editingId ? "Edit patient intake" : "Patient intake"} onClose={() => setOpen(false)}>
          <form className="form-grid" onSubmit={onSave}>
            <Field label="Patient full name">
              <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </Field>
            <Field label="Registration number" hint="Observed format HCTM26-#### is accepted; other future formats are allowed.">
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
            <Field label="Registration date">
              <input type="date" value={form.registered_at} onChange={(e) => setForm({ ...form, registered_at: e.target.value })} />
            </Field>
            <Field label="Registered online">
              <select value={form.registered_online ? "yes" : "no"} onChange={(e) => setForm({ ...form, registered_online: e.target.value === "yes" })}>
                <option value="no">No</option>
                <option value="yes">Yes</option>
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
            <div style={{ gridColumn: "1 / -1" }}>
              <strong>Guardians</strong>
              {form.guardians.map((guardian, index) => (
                <div className="form-grid" key={index} style={{ marginTop: 8 }}>
                  <Field label="Guardian name">
                    <input value={guardian.name} onChange={(e) => {
                      const next = [...form.guardians];
                      next[index] = { ...guardian, name: e.target.value };
                      setForm({ ...form, guardians: next });
                    }} />
                  </Field>
                  <Field label="Relationship">
                    <input value={guardian.relationship} onChange={(e) => {
                      const next = [...form.guardians];
                      next[index] = { ...guardian, relationship: e.target.value };
                      setForm({ ...form, guardians: next });
                    }} />
                  </Field>
                  <Field label="Contact">
                    <input value={guardian.contact} onChange={(e) => {
                      const next = [...form.guardians];
                      next[index] = { ...guardian, contact: e.target.value };
                      setForm({ ...form, guardians: next });
                    }} />
                  </Field>
                  {form.guardians.length > 1 ? (
                    <button
                      type="button"
                      className="btn secondary"
                      style={{ alignSelf: "end" }}
                      onClick={() => setForm({ ...form, guardians: form.guardians.filter((_, i) => i !== index) })}
                    >
                      Remove guardian
                    </button>
                  ) : null}
                </div>
              ))}
              <button
                type="button"
                className="btn secondary"
                style={{ marginTop: 8 }}
                onClick={() => setForm({ ...form, guardians: [...form.guardians, { name: "", relationship: "", contact: "" }] })}
              >
                Add guardian
              </button>
            </div>
            <div className="sensitive" style={{ gridColumn: "1 / -1" }}>
              <strong>Social worker assessment</strong>
              <p className="muted">Exact room-fee fields are not yet confirmed in the PRD. Capture notes and an optional assessed amount only. Additional confirmed fields can be stored later in the JSON payload.</p>
              <Field label="Assessment notes">
                <textarea value={form.assessment_notes} onChange={(e) => setForm({ ...form, assessment_notes: e.target.value })} />
              </Field>
              <Field label="Optional assessed fee (RM)">
                <input type="number" min={0} step="0.01" value={form.assessed_fee_amount} onChange={(e) => setForm({ ...form, assessed_fee_amount: e.target.value })} />
              </Field>
            </div>
            <button className="btn" type="submit">{editingId ? "Save changes" : "Save intake"}</button>
          </form>
        </Modal>
      ) : null}

      {detail ? (
        <Modal title={detail.name} onClose={() => setDetail(null)}>
          <p>
            <strong>{detail.registration_no}</strong> · {detail.ward_clinic.name} · {detail.state.name}
          </p>
          <p>
            Status <span className={`badge ${detail.status}`}>{detail.status}</span>
            {detail.registered_online ? " · Registered online" : ""}
          </p>
          {detail.nric ? <p>NRIC: {detail.nric}</p> : <p className="muted">Sensitive identity fields (NRIC, diagnosis, guardians) are hidden for this role.</p>}
          {detail.dob ? <p>Date of birth: {detail.dob}</p> : null}
          {detail.gender ? <p>Gender: {detail.gender}</p> : null}
          {detail.diagnosis ? <p>Diagnosis: {detail.diagnosis}</p> : null}
          {detail.referring_doctor ? <p>Referring doctor: {detail.referring_doctor}</p> : null}
          {detail.address ? <p>Address: {detail.address}</p> : null}
          <p>Siblings: {detail.sibling_count}{detail.sibling_names ? ` (${detail.sibling_names})` : ""}</p>
          {detail.guardians?.map((g) => (
            <p key={`${g.name}-${g.contact}`}>
              Guardian: {g.name} ({g.relationship}) {g.contact}
            </p>
          ))}
          {detail.assessment ? (
            <div className="sensitive">
              <strong>Assessment</strong>
              <p>{detail.assessment.notes || "No notes recorded."}</p>
              {detail.assessment.assessed_fee_amount ? <p>Assessed fee (RM): {detail.assessment.assessed_fee_amount}</p> : null}
            </div>
          ) : null}
          {canWrite && canSensitive ? (
            <button
              className="btn"
              style={{ marginTop: 12 }}
              onClick={() => {
                setDetail(null);
                openEdit(detail.id);
              }}
            >
              Edit intake
            </button>
          ) : null}
          {can(user, "patients:delete") ? (
            <button
              className="btn danger"
              style={{ marginTop: 12, marginLeft: 8 }}
              onClick={async () => {
                if (!window.confirm(`Delete intake for ${detail.name}? This cannot be undone.`)) return;
                try {
                  await api(`/api/patients/${detail.id}`, { method: "DELETE" });
                  setDetail(null);
                  setSuccess("Patient record deleted.");
                  await load();
                } catch (err) {
                  setError(err instanceof HttpError ? err.message : "Unable to delete");
                }
              }}
            >
              Delete
            </button>
          ) : null}
        </Modal>
      ) : null}
    </AppShell>
  );
}
