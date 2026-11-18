import { useState } from 'react';
import type { SyntheticEvent } from 'react';
import { ApiError } from '../api/http';
import type { FieldErrors } from '../api/http';

/**
 * Runs a form action, exposing the refusal and an in-flight flag.
 *
 * Field errors for names in `inlineFields` come back in `fieldErrors` for the
 * form to show beside each input. Any other field error is folded into `error`
 * with its field name, so a refusal is never silently dropped.
 *
 *     const { error, fieldErrors, submitting, onSubmit } = useSubmit(save, ['title']);
 */
export function useSubmit(action: () => Promise<void>, inlineFields: readonly string[] = []) {
  const [refusal, setRefusal] = useState<ApiError | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: SyntheticEvent) {
    e.preventDefault();
    setRefusal(null);
    setSubmitting(true);
    try {
      await action();
    } catch (err) {
      if (!(err instanceof ApiError)) throw err;
      setRefusal(err);
    } finally {
      setSubmitting(false);
    }
  }

  const fieldErrors: Record<string, string> = {};
  const messages = refusal?.message ? [refusal.message] : [];
  for (const [field, message] of Object.entries(refusal?.fieldErrors ?? {})) {
    if (inlineFields.includes(field)) fieldErrors[field] = message;
    else messages.push(`${field}: ${message}`);
  }

  return {
    error: messages.length > 0 ? messages.join(' ') : null,
    fieldErrors: fieldErrors as FieldErrors,
    submitting,
    onSubmit,
    clear: () => setRefusal(null),
  };
}
