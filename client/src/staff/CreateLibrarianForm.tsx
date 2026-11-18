import { useState } from 'react';
import { FieldError } from '../components/FieldError';
import { invalidProps } from '../components/invalidProps';
import { useSubmit } from '../hooks/useSubmit';
import { createLibrarian } from './api';
import type { StaffMember } from './api';

/** Creates a librarian account with a starting password chosen by the admin. */
export function CreateLibrarianForm({ onCreated }: { onCreated: () => void }) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [created, setCreated] = useState<StaffMember | null>(null);
  const { error, fieldErrors, submitting, onSubmit } = useSubmit(async () => {
    setCreated(null);
    setCreated(await createLibrarian({ name, email, password }));
    setName('');
    setEmail('');
    setPassword('');
    onCreated();
  }, ['name', 'email', 'password']);

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
        {...invalidProps('staff-name', fieldErrors.name)}
      />
      <FieldError inputId="staff-name" message={fieldErrors.name} />
      <label htmlFor="staff-email">Email</label>
      <input
        id="staff-email"
        type="email"
        autoComplete="off"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        required
        {...invalidProps('staff-email', fieldErrors.email)}
      />
      <FieldError inputId="staff-email" message={fieldErrors.email} />
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
        {...invalidProps('staff-password', fieldErrors.password)}
      />
      <FieldError inputId="staff-password" message={fieldErrors.password} />
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
