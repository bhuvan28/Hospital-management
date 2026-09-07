"use client";

import { useEffect, useState } from "react";
import { AppShell, can, useUser } from "@/components/AppShell";
import { Banner, Empty, Loading, PageHeader } from "@/components/ui";
import { api } from "@/lib/api";
import type { OccupancySummary, OccupantRow, WaitlistEntry } from "@/lib/types";

type Dashboard = {
  role: string;
  occupancy?: OccupancySummary;
  patient_census?: number;
  current_occupants?: OccupantRow[];
  open_waitlist?: WaitlistEntry[];
  todays_movements?: { check_ins: OccupantRow[]; check_outs: OccupantRow[] };
  donations?: { annual_total: string; monthly_total: string; total_count: number };
  petty_cash?: { total_budgeted: string; total_actual: string; total_balance: string };
  meals?: { monthly_total: string; total_pax: number };
  note?: string;
  message?: string;
};

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="card">
      <div className="muted">{label}</div>
      <div className="stat-value">{value}</div>
    </div>
  );
}

function OccupantTable({ rows, empty }: { rows: OccupantRow[]; empty: string }) {
  if (!rows.length) return <Empty>{empty}</Empty>;
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Room</th>
            <th>Patient</th>
            <th>Registration</th>
            <th>Ward</th>
            <th>Check-in</th>
            <th>Officer</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={`${row.stay_id}-${row.room_number}`}>
              <td>{row.room_number}</td>
              <td>{row.patient_name}</td>
              <td>{row.registration_no}</td>
              <td>{row.ward_name || "—"}</td>
              <td>{row.check_in_date}</td>
              <td>{row.officer_name || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function DashboardPage() {
  const user = useUser();
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api<Dashboard>("/api/dashboard")
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <AppShell>
      <PageHeader title="Dashboard" subtitle="Live figures from the house database. Occupancy is never entered by hand." />
      {error ? <Banner kind="error">{error}</Banner> : null}
      {data?.note ? <Banner kind="info">{data.note}</Banner> : null}
      {data?.message ? <Banner kind="info">{data.message}</Banner> : null}
      {loading && !data ? <Loading>Loading dashboard…</Loading> : null}
      {data?.occupancy ? (
        <div className="grid stats" style={{ marginBottom: 16 }}>
          <Stat label="Total rooms" value={data.occupancy.total_rooms} />
          <Stat label="Occupied" value={data.occupancy.occupied_rooms} />
          <Stat label="Vacant" value={data.occupancy.vacant_rooms} />
          <Stat label="Maintenance" value={data.occupancy.maintenance_rooms} />
          <Stat label="Occupancy rate" value={`${data.occupancy.occupancy_rate}%`} />
          <Stat label="Today check-ins" value={data.occupancy.todays_check_ins} />
          <Stat label="Today check-outs" value={data.occupancy.todays_check_outs} />
          <Stat label="Waiting list" value={data.occupancy.waiting_list_open} />
          {data.patient_census !== undefined ? <Stat label="Patient census" value={data.patient_census} /> : null}
        </div>
      ) : null}
      {can(user, "dashboard:finance") && data?.donations ? (
        <div className="grid stats" style={{ marginBottom: 16 }}>
          <Stat label="Donations this year (RM)" value={data.donations.annual_total} />
          <Stat label="Donations this month (RM)" value={data.donations.monthly_total} />
          <Stat label="Donation records" value={data.donations.total_count} />
          {data.petty_cash ? <Stat label="Petty cash balance (RM)" value={data.petty_cash.total_balance} /> : null}
          {data.meals ? <Stat label="Meal sponsorship this month (RM)" value={data.meals.monthly_total} /> : null}
        </div>
      ) : null}
      {data?.current_occupants ? (
        <div className="card" style={{ marginBottom: 16 }}>
          <h2>Current occupants</h2>
          <OccupantTable rows={data.current_occupants} empty="No families are currently occupying rooms." />
        </div>
      ) : null}
      {data?.open_waitlist ? (
        <div className="card" style={{ marginBottom: 16 }}>
          <h2>Waiting list</h2>
          {!data.open_waitlist.length ? (
            <Empty>No families currently waiting.</Empty>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Patient</th>
                    <th>Registration</th>
                    <th>Added</th>
                    <th>Days waited</th>
                  </tr>
                </thead>
                <tbody>
                  {data.open_waitlist.map((row) => (
                    <tr key={row.id}>
                      <td>{row.patient_name}</td>
                      <td>{row.registration_no}</td>
                      <td>{row.added_date}</td>
                      <td>{row.days_waited}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : null}
      {data?.todays_movements ? (
        <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))" }}>
          <div className="card">
            <h2>Today&apos;s check-ins</h2>
            <OccupantTable rows={data.todays_movements.check_ins} empty="No check-ins today." />
          </div>
          <div className="card">
            <h2>Today&apos;s check-outs</h2>
            <OccupantTable rows={data.todays_movements.check_outs} empty="No check-outs today." />
          </div>
        </div>
      ) : null}
    </AppShell>
  );
}
