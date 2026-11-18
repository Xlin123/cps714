import { getJson } from '../api/http';
import { HISTORY_PAGE_SIZE } from '../lending/api';
import type { LoanStatus, MemberLoanPage } from '../lending/api';

/** A member account as staff see it. */
export interface Member {
  id: string;
  name: string;
  email: string;
  is_active: boolean;
}

export interface MemberPage {
  items: Member[];
  total: number;
}

export interface MemberProfile extends Member {
  active_loans: number;
  total_loans: number;
}

/** Page size for member search; the server rejects anything above 100. */
export const MEMBER_SEARCH_LIMIT = 50;

/** Members whose name or email contains `query`; an empty query lists everyone. */
export async function searchMembers(query: string): Promise<MemberPage> {
  const params = new URLSearchParams({ q: query, limit: String(MEMBER_SEARCH_LIMIT) });
  return getJson<MemberPage>(`/api/members?${params}`);
}

export async function fetchMember(id: string): Promise<MemberProfile> {
  return getJson<MemberProfile>(`/api/members/${encodeURIComponent(id)}`);
}

/** A member's loans, most recently checked out first. */
export async function fetchMemberLoans(
  id: string,
  status: LoanStatus,
  offset: number,
): Promise<MemberLoanPage> {
  const params = new URLSearchParams({
    status,
    limit: String(HISTORY_PAGE_SIZE),
    offset: String(offset),
  });
  return getJson<MemberLoanPage>(`/api/members/${encodeURIComponent(id)}/loans?${params}`);
}
