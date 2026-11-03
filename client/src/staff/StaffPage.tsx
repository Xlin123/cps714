import { useLoad } from '../hooks/useLoad';
import { fetchStaff, STAFF_LIST_LIMIT } from './api';
import { CreateLibrarianForm } from './CreateLibrarianForm';
import { StaffTable } from './StaffTable';

/** Admin page for creating and deactivating librarian accounts. */
export function StaffPage() {
  const { state, reload } = useLoad(fetchStaff, []);

  return (
    <div className="page wide">
      <h1>Staff accounts</h1>
      <h2>Add a librarian</h2>
      <CreateLibrarianForm onCreated={reload} />
      <h2>Librarians</h2>
      {state.status === 'loading' && <p>Loading…</p>}
      {state.status === 'failed' && (
        <p className="error">Could not load staff accounts: {state.error}</p>
      )}
      {state.status === 'loaded' && (
        <>
          <StaffTable staff={state.data.items} onChanged={reload} />
          {state.data.total > STAFF_LIST_LIMIT && (
            <p>
              Showing the first {STAFF_LIST_LIMIT} of {state.data.total} accounts.
            </p>
          )}
        </>
      )}
    </div>
  );
}
