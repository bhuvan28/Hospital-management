export type Role = "duty_officer" | "social_worker" | "admin" | "finance" | "viewer";

export type NavItem = { href: string; label: string };

export type CurrentUser = {
  id: number;
  name: string;
  email: string;
  role: Role;
  active: boolean;
  permissions: string[];
  navigation: NavItem[];
};

export type Page<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
};

export type Lookup = { id: number; name: string; active: boolean };

export type Guardian = { id?: number; name: string; relationship: string; contact: string };

export type PatientList = {
  id: number;
  name: string;
  registration_no: string;
  gender: string;
  status: string;
  ward_clinic: Lookup;
  state: Lookup;
  registered_at: string;
  registered_online: boolean;
  nric: string | null;
  diagnosis: string | null;
  house_status?: "in_house" | "waiting" | "none";
  room_number?: string | null;
};

export type PatientDetail = PatientList & {
  dob: string | null;
  address: string | null;
  referring_doctor: string | null;
  sibling_count: number;
  sibling_names: string | null;
  guardians: Guardian[];
  assessment: {
    id: number;
    payload: Record<string, unknown>;
    notes: string | null;
    assessed_fee_amount: string | null;
    assessed_by_id: number | null;
    assessed_at: string | null;
  } | null;
};

export type Occupant = {
  patient_id: number;
  patient_name: string;
  registration_no: string;
  ward_name: string | null;
  check_in_date: string;
  officer_name: string | null;
  room_inspected: boolean;
  remarks: string | null;
  stay_id: number;
};

export type Room = {
  id: number;
  room_number: string;
  status: "vacant" | "occupied" | "maintenance";
  occupancy_status?: "vacant" | "occupied" | "maintenance";
  notes: string | null;
  current_occupant: Occupant | null;
};

export function occupancyStatus(room: Room): "vacant" | "occupied" | "maintenance" {
  if (room.occupancy_status) return room.occupancy_status;
  if (room.current_occupant) return "occupied";
  if (room.status === "maintenance") return "maintenance";
  return "vacant";
}

export type OccupancySummary = {
  total_rooms: number;
  occupied_rooms: number;
  vacant_rooms: number;
  maintenance_rooms: number;
  occupancy_rate: number;
  todays_check_ins: number;
  todays_check_outs: number;
  waiting_list_open: number;
};

export type OccupantRow = {
  stay_id: number;
  room_id: number;
  room_number: string;
  patient_id: number;
  patient_name: string;
  registration_no: string;
  ward_name: string | null;
  check_in_date: string;
  check_out_date?: string | null;
  officer_name: string | null;
  room_inspected?: boolean;
  remarks?: string | null;
};

export type DonationSummary = {
  total_amount: string;
  monthly_total: string;
  annual_total: string;
  total_count: number;
  by_type: Record<string, string>;
  by_category: Record<string, string>;
  monthly_by_type: Record<string, string>;
  monthly_by_category: Record<string, string>;
};

export type Stay = {
  id: number;
  patient_id: number;
  room_id: number;
  hospital_admission_date: string | null;
  check_in_date: string;
  check_out_date: string | null;
  officer_on_duty_id: number | null;
  room_inspected: boolean;
  remarks: string | null;
  patient_name: string | null;
  registration_no: string | null;
  room_number: string | null;
  officer_name: string | null;
};

export type WaitlistEntry = {
  id: number;
  patient_id: number;
  patient_name: string;
  registration_no: string;
  added_date: string;
  resolved_date: string | null;
  days_waited: number;
  remarks: string | null;
};

export type ApiError = { error: { message: string; code: string; details?: { field: string; message: string }[] } };
