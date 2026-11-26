import { ActionButton } from '../components/ActionButton';
import { useLoad } from '../hooks/useLoad';
import { cancelHold, fetchMyHolds } from './api';
import type { Hold } from './api';

function status(hold: Hold): string {
  if (hold.is_ready) return 'Ready for pickup';
  return hold.position === 1 ? 'Next in line' : `${hold.position} in line`;
}

/** The signed-in member's holds, with ready ones called out (LMS-16). */
export function MyHolds() {
  const { state, reload } = useLoad(fetchMyHolds, []);

  return (
    <section aria-labelledby="holds-heading">
      <h2 id="holds-heading">Holds</h2>
      {state.status === 'loading' && <p>Loading…</p>}
      {state.status === 'failed' && (
        <p className="error">Could not load your holds: {state.error}</p>
      )}
      {state.status === 'loaded' && <HoldList holds={state.data.items} onChange={reload} />}
    </section>
  );
}

function HoldList({ holds, onChange }: { holds: Hold[]; onChange: () => void }) {
  if (holds.length === 0) {
    return <p>You have no holds. Place one from the catalogue when every copy is out.</p>;
  }
  const ready = holds.filter((hold) => hold.is_ready);

  return (
    <>
      {ready.length > 0 && (
        <ul className="notices">
          {ready.map((hold) => (
            <li key={hold.id} className="notice ready">
              <span>
                <strong>{hold.book_title}</strong> is ready for pickup at the desk.
              </span>
            </li>
          ))}
        </ul>
      )}
      <div className="table-scroll">
        <table className="catalog">
          <thead>
            <tr>
              <th scope="col">Book</th>
              <th scope="col">Placed</th>
              <th scope="col">Status</th>
              <th scope="col" className="action-column">
                <span className="visually-hidden">Action</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {holds.map((hold) => (
              <tr key={hold.id}>
                <td>{hold.book_title}</td>
                <td>{new Date(hold.placed_at).toLocaleDateString()}</td>
                <td className={hold.is_ready ? 'ready' : undefined}>{status(hold)}</td>
                <td>
                  <ActionButton
                    label="Cancel"
                    busyLabel="Cancelling…"
                    accessibleLabel={`Cancel hold on ${hold.book_title}`}
                    action={async () => {
                      await cancelHold(hold.id);
                      onChange();
                    }}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
