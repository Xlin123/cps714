import { getJson } from '../api/http';
import type { BookLoanCount } from '../dashboard/api';

export interface WeekCount {
  /** A Monday, `YYYY-MM-DD`, UTC. */
  week_start: string;
  loans: number;
}

export interface CategoryCount {
  category: string;
  loans: number;
}

/** Lending from `period_start` until now, over `weeks` weeks. */
export interface Report {
  period_start: string;
  weeks: number;
  totals: { loans: number; borrowers: number };
  loans_per_week: WeekCount[];
  popular_titles: BookLoanCount[];
  popular_categories: CategoryCount[];
}

/** The period choices offered; the server accepts 1–52 weeks. */
export const WEEK_PRESETS = [4, 12, 26, 52] as const;

export async function fetchReport(weeks: number): Promise<Report> {
  return getJson<Report>(`/api/reports?weeks=${weeks}`);
}
