import { useState } from 'react';
import type { ReactNode } from 'react';
import { useLocation } from 'react-router-dom';
import { useAuth } from '../auth/useAuth';
import { useLoad } from '../hooks/useLoad';
import { fetchMyReminders } from './api';
import { RemindersContext } from './useReminders';

const storageKey = (userId: string) => `lms.dismissedReminders.${userId}`;

/** Loan ids whose due-soon reminder this user dismissed in this browser. */
function readDismissed(userId: string | undefined): number[] {
  if (!userId) return [];
  try {
    const parsed: unknown = JSON.parse(localStorage.getItem(storageKey(userId)) ?? '[]');
    return Array.isArray(parsed) ? parsed.filter((id) => typeof id === 'number') : [];
  } catch {
    // Storage blocked or corrupt: show every reminder rather than fail.
    return [];
  }
}

function writeDismissed(userId: string, ids: number[]) {
  try {
    localStorage.setItem(storageKey(userId), JSON.stringify(ids));
  } catch {
    // Storage blocked: the dismissal lasts until the page reloads.
  }
}

/**
 * Loads the signed-in member's reminders and refetches on every navigation, so
 * the nav badge catches up soon after a return without polling.
 */
export function RemindersProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const { pathname } = useLocation();
  const userId = user?.id;
  const canView = user?.capabilities.includes('view_own_loans') ?? false;
  const { state } = useLoad(
    async () => (canView ? { page: await fetchMyReminders(), loadedAt: Date.now() } : null),
    [canView, userId, pathname],
  );
  // Remembers this session's dismissals; storage is reread when the user changes.
  const [stored, setStored] = useState<{ userId?: string; ids: number[] }>({ ids: [] });
  const dismissed = stored.userId === userId ? stored.ids : readDismissed(userId);

  // A failed load shows no reminders; the history table still shows each status.
  const loaded = state.status === 'loaded' ? state.data : null;
  const all = loaded?.page.items ?? [];
  const reminders = all.filter(
    (loan) => loan.reminder === 'overdue' || !dismissed.includes(loan.id),
  );

  function dismiss(loanId: number) {
    if (!userId) return;
    // Keep only ids still due soon, so storage cannot grow without bound.
    const dueSoon = new Set(all.filter((l) => l.reminder === 'due_soon').map((l) => l.id));
    const next = [...dismissed.filter((id) => dueSoon.has(id)), loanId];
    writeDismissed(userId, next);
    setStored({ userId, ids: next });
  }

  return (
    <RemindersContext.Provider
      value={{ reminders, loadedAt: loaded?.loadedAt ?? 0, dismiss }}
    >
      {children}
    </RemindersContext.Provider>
  );
}
