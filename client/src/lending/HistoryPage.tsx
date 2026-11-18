import { useState } from 'react';
import { useLoad } from '../hooks/useLoad';
import { fetchMyLoans } from './api';
import type { LoanStatus } from './api';
import { LoanStatusFilter, LoanTable } from './LoanTable';
import { ReminderNotices } from './ReminderNotices';

const EMPTY_TEXT: Record<LoanStatus, string> = {
  all: "You haven't borrowed any books yet.",
  active: 'You have no books on loan.',
  returned: "You haven't returned any books yet.",
};

/** The signed-in member's borrowing history (LMS-12). */
export function HistoryPage() {
  const [status, setStatus] = useState<LoanStatus>('all');
  const [offset, setOffset] = useState(0);
  const { state } = useLoad(() => fetchMyLoans(status, offset), [status, offset]);

  const chooseStatus = (next: LoanStatus) => {
    setStatus(next);
    setOffset(0);
  };

  return (
    <div className="page wide">
      <h1>My loans</h1>
      <ReminderNotices />
      <LoanStatusFilter status={status} onChange={chooseStatus} />
      {state.status === 'loading' && <p>Loading…</p>}
      {state.status === 'failed' && (
        <p className="error">Could not load your loans: {state.error}</p>
      )}
      {state.status === 'loaded' &&
        (state.data.total === 0 ? (
          <p>{EMPTY_TEXT[status]}</p>
        ) : (
          <LoanTable page={state.data} offset={offset} onPage={setOffset} />
        ))}
    </div>
  );
}
