import { useState } from 'react';
import type { FormEvent } from 'react';
import { useAuth } from '../auth/AuthContext';

export function RegisterPage() {
  const { pendingEmail, refresh } = useAuth();
  const [name, setName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const res = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(data.error ?? 'Registration failed.');
        return;
      }
      await refresh();
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="page">
      <h1>Complete registration</h1>
      <p>Signed in as {pendingEmail}. Finish creating your member account.</p>
      <form onSubmit={handleSubmit}>
        <label htmlFor="name">Name</label>
        <input id="name" value={name} onChange={(e) => setName(e.target.value)} required />
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={submitting}>
          {submitting ? 'Creating account…' : 'Create account'}
        </button>
      </form>
    </div>
  );
}
