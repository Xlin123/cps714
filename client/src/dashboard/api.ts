import { getJson } from '../api/http';
import type { MemberLoanPage } from '../lending/api';

export interface DashboardCounts {
  titles: number;
  copies: number;
  on_loan: number;
  overdue: number;
  holds_waiting: number;
  active_members: number;
}

export interface BookLoanCount {
  book_id: number;
  title: string;
  author: string;
  loans: number;
}

/** `overdue` holds at most 100 loans, longest overdue first; its `total` counts all. */
export interface Dashboard {
  counts: DashboardCounts;
  most_borrowed: BookLoanCount[];
  overdue: MemberLoanPage;
}

export async function fetchDashboard(): Promise<Dashboard> {
  return getJson<Dashboard>('/api/dashboard');
}
