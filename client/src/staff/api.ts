import { getJson, jsonBody, send } from '../api/http';

export interface StaffMember {
  id: string;
  email: string;
  name: string;
  is_active: boolean;
}

export interface StaffPage {
  items: StaffMember[];
  total: number;
}

export interface LibrarianInput {
  email: string;
  name: string;
  password: string;
}

/** The server's page-size cap; the staff table shows at most this many. */
export const STAFF_LIST_LIMIT = 100;

export async function fetchStaff(): Promise<StaffPage> {
  return getJson<StaffPage>(`/api/staff?limit=${STAFF_LIST_LIMIT}`);
}

export async function createLibrarian(input: LibrarianInput): Promise<StaffMember> {
  const res = await send('/api/staff', jsonBody('POST', input), 'Could not create the account.');
  return res.json();
}

export async function setStaffActive(id: string, isActive: boolean): Promise<StaffMember> {
  const res = await send(
    `/api/staff/${id}`,
    jsonBody('PATCH', { is_active: isActive }),
    'Could not update the account.',
  );
  return res.json();
}
