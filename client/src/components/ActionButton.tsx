import { useSubmit } from '../hooks/useSubmit';

/**
 * A button that runs one server action, with an in-flight label and the
 * server's refusal shown beside it. For per-row actions in tables.
 *
 *     <ActionButton label="Check in" busyLabel="Checking in…" action={() => checkIn(id)} />
 */
export function ActionButton({
  label,
  busyLabel,
  accessibleLabel,
  action,
}: {
  label: string;
  busyLabel: string;
  /** Names the row too, since every row has a button with the same text. */
  accessibleLabel: string;
  action: () => Promise<void>;
}) {
  const { error, submitting, onSubmit } = useSubmit(action);

  return (
    <form onSubmit={onSubmit}>
      <button type="submit" disabled={submitting} aria-label={accessibleLabel}>
        {submitting ? busyLabel : label}
      </button>
      {error && <p className="error">{error}</p>}
    </form>
  );
}
