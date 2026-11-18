import { errorIdFor } from './invalidProps';

/** A field's error shown under its input, announced when it appears. */
export function FieldError({ inputId, message }: { inputId: string; message: string | undefined }) {
  if (!message) return null;
  return (
    <p id={errorIdFor(inputId)} className="field-error" role="alert">
      {message}
    </p>
  );
}
