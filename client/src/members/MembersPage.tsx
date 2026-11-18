import { useState } from 'react';
import type { FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { useLoad } from '../hooks/useLoad';
import { MEMBER_SEARCH_LIMIT, searchMembers } from './api';
import type { Member } from './api';

/** Staff page for finding a member by name or email (LMS-13). */
export function MembersPage() {
  const [draft, setDraft] = useState('');
  const [query, setQuery] = useState('');
  const { state } = useLoad(() => searchMembers(query), [query]);

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    setQuery(draft.trim());
  }

  return (
    <div className="page wide">
      <h1>Members</h1>
      <form className="member-search" role="search" onSubmit={onSubmit}>
        <label htmlFor="member-query">Name or email</label>
        <input
          id="member-query"
          type="search"
          maxLength={100}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
        />
        <button type="submit">Search</button>
      </form>
      {state.status === 'loading' && <p>Loading…</p>}
      {state.status === 'failed' && (
        <p className="error">Could not load members: {state.error}</p>
      )}
      {state.status === 'loaded' && (
        <>
          <MemberTable members={state.data.items} query={query} />
          {state.data.total > MEMBER_SEARCH_LIMIT && (
            <p>
              Showing the first {MEMBER_SEARCH_LIMIT} of {state.data.total} members. Narrow
              the search to see others.
            </p>
          )}
        </>
      )}
    </div>
  );
}

function MemberTable({ members, query }: { members: Member[]; query: string }) {
  if (members.length === 0) {
    return <p>{query ? `No members match “${query}”.` : 'No member accounts yet.'}</p>;
  }

  return (
    <div className="table-scroll">
      <table className="catalog">
        <thead>
          <tr>
            <th scope="col">Name</th>
            <th scope="col">Email</th>
            <th scope="col">Status</th>
          </tr>
        </thead>
        <tbody>
          {members.map((member) => (
            <tr key={member.id}>
              <td>
                <Link to={`/members/${member.id}`}>{member.name}</Link>
              </td>
              <td>{member.email}</td>
              <td className={member.is_active ? undefined : 'unavailable'}>
                {member.is_active ? 'Active' : 'Deactivated'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
