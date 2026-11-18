import { createContext, useContext } from 'react';
import type { MemberLoan } from './api';

export interface RemindersState {
  /** Overdue and due-soon loans still worth showing, soonest due first. */
  reminders: MemberLoan[];
  /** True once reminders have loaded; false while loading, after a failure, or for staff. */
  isLoaded: boolean;
  /** When `reminders` was fetched (ms since epoch), for "due in N days" wording. */
  loadedAt: number;
  /** Hides a due-soon reminder in this browser. Overdue reminders cannot be hidden. */
  dismiss: (loanId: number) => void;
}

export const RemindersContext = createContext<RemindersState | undefined>(undefined);

/**
 * The signed-in member's loan reminders; empty for guests and staff.
 *
 *     const { reminders } = useReminders();
 */
export function useReminders(): RemindersState {
  const ctx = useContext(RemindersContext);
  if (!ctx) throw new Error('useReminders must be used within a RemindersProvider');
  return ctx;
}
