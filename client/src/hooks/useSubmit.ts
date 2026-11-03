import { useState } from 'react';
import type { FormEvent } from 'react';
import { ApiError } from '../api/http';

/** Runs a form action, exposing a user-facing error and an in-flight flag. */
export function useSubmit(action: () => Promise<void>) {
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await action();
    } catch (err) {
      if (!(err instanceof ApiError)) throw err;
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return { error, submitting, onSubmit };
}
