import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useLoad } from '../hooks/useLoad';
import type { LoanStatus } from '../lending/api';
import { LoanStatusFilter, LoanTable } from '../lending/LoanTable';
import { formatCents } from '../lending/money';
import { fetchMember, fetchMemberLoans } from './api';

const EMPTY_TEXT: Record<LoanStatus, string> = {
  all: 'This member has not borrowed any books.',
  active: 'This member has no books on loan.',
  returned: 'This member has not returned any books.',
};

/** A member's details and loan history, for staff helping them (LMS-13). */
export function MemberProfilePage() {
  const { id = '' } = useParams();
  const [status, setStatus] = useState<LoanStatus>('all');
  const [offset, setOffset] = useState(0);
  const profile = useLoad(() => fetchMember(id), [id]).state;
  const loans = useLoad(() => fetchMemberLoans(id, status, offset), [id, status, offset]).state;

  const chooseStatus = (next: LoanStatus) => {
    setStatus(next);
    setOffset(0);
  };

  return (
    <div className="page wide">
      <p>
        <Link to="/members">← All members</Link>
      </p>
      {profile.status === 'loading' && <p>Loading…</p>}
      {profile.status === 'failed' && (
        <p className="error">Could not load this member: {profile.error}</p>
      )}
      {profile.status === 'loaded' && (
        <>
          <h1>{profile.data.name}</h1>
          <dl className="member-details">
            <dt>Email</dt>
            <dd>{profile.data.email}</dd>
            <dt>Status</dt>
            <dd>{profile.data.is_active ? 'Active' : 'Deactivated'}</dd>
            <dt>On loan</dt>
            <dd>{profile.data.active_loans}</dd>
            <dt>Loans ever</dt>
            <dd>{profile.data.total_loans}</dd>
            <dt>Fines</dt>
            <dd>{formatCents(profile.data.fines_cents)}</dd>
          </dl>
          <h2>Loans</h2>
          <LoanStatusFilter status={status} onChange={chooseStatus} />
          {loans.status === 'loading' && <p>Loading…</p>}
          {loans.status === 'failed' && (
            <p className="error">Could not load loans: {loans.error}</p>
          )}
          {loans.status === 'loaded' &&
            (loans.data.total === 0 ? (
              <p>{EMPTY_TEXT[status]}</p>
            ) : (
              <LoanTable page={loans.data} offset={offset} onPage={setOffset} />
            ))}
        </>
      )}
    </div>
  );
}
