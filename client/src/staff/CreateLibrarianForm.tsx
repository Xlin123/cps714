import { useState } from 'react';
import { useSubmit } from '../hooks/useSubmit';
import { createLibrarian } from './api';
import type { StaffMember } from './api';

/** Creates a librarian account with a starting password chosen by the admin. */
export function CreateLibrarianForm({ onCreated }: { onCreated: () => void }) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [created, setCreated] = useState<StaffMember | null>(null);
  const { error, submitting, onSubmit } = useSubmit(async () => {
    setCreated(null);
    setCreated(await createLibrarian({ name, email, password }));
    setName('');
    setEmail('');
    setPassword('');
    onCreated();
  });

  return (
    <form className="narrow" onSubmit={onSubmit}>
      <label htmlFor="staff-name">Name</label>
      <input
        id="staff-name"
        autoComplete="off"
        maxLength={100}
        value={name}
        onChange={(e) => setName(e.target.value)}
        required
      />
      <label htmlFor="staff-email">Email</label>
      <input
        id="staff-email"
        type="email"
        autoComplete="off"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        required
      />
      <label htmlFor="staff-password">Starting password</label>
      <input
        id="staff-password"
        type="password"
        autoComplete="new-password"
        minLength={8}
        maxLength={128}
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
      />
      {error && <p className="error">{error}</p>}
      {created && (
        <p role="status">
          Created {created.name} ({created.email}). Give them the starting password in person.
        </p>
      )}
      <button type="submit" disabled={submitting}>
        {submitting ? 'Creating…' : 'Create librarian'}
      </button>
    </form>
  );
}
