"use client";

import { useEffect, useState } from "react";
import { AppShell, can, useUser } from "@/components/AppShell";
import { PageHeader } from "@/components/ui";
import { api } from "@/lib/api";
import type { OccupancySummary } from "@/lib/types";

type Dashboard = {
  role: string;
  occupancy?: OccupancySummary;
  patient_census?: number;
  donations?: { annual_total: string; monthly_total: string; total_count: number };
  petty_cash?: { total_budgeted: string; total_actual: string; total_balance: string };
  meals?: { monthly_total: string; total_pax: number };
  note?: string;
};

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="card">
      <div className="muted">{label}</div>
      <div className="stat-value">{value}</div>
    </div>
  );
}

export default function DashboardPage() {
  const user = useUser();
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Dashboard>("/api/dashboard")
      .then(setData)
      .catch((err) => setError(err.message));
  }, []);

  return (
    <AppShell>
      <PageHeader title="Dashboard" subtitle="Live figures from the house database. Occupancy is never entered by hand." />
      {error ? <div className="banner error">{error}</div> : null}
      {data?.note ? <div className="banner info">{data.note}</div> : null}
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
        <div className="grid stats">
          <Stat label="Donations this year (RM)" value={data.donations.annual_total} />
          <Stat label="Donations this month (RM)" value={data.donations.monthly_total} />
          <Stat label="Donation records" value={data.donations.total_count} />
          {data.petty_cash ? <Stat label="Petty cash balance (RM)" value={data.petty_cash.total_balance} /> : null}
          {data.meals ? <Stat label="Meal sponsorship this month (RM)" value={data.meals.monthly_total} /> : null}
        </div>
      ) : null}
    </AppShell>
  );
}
