/** The id of the `FieldError` element that describes input `inputId`. */
export const errorIdFor = (inputId: string) => `${inputId}-error`;

/**
 * Accessibility attributes linking an input to its `FieldError`.
 *
 *     <input id="book-title" {...invalidProps('book-title', fieldErrors.title)} />
 *     <FieldError inputId="book-title" message={fieldErrors.title} />
 */
export function invalidProps(inputId: string, message: string | undefined) {
  if (!message) return {};
  return { 'aria-invalid': true, 'aria-describedby': errorIdFor(inputId) } as const;
}
