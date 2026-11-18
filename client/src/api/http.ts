/** Messages keyed by the field they belong to, using the API's field names. */
export type FieldErrors = Readonly<Record<string, string>>;

/**
 * An action refused by the server or by a client-side check, worded for the
 * user. `message` covers the action as a whole and may be empty when every
 * problem belongs to a field in `fieldErrors`.
 *
 *     throw new ApiError('', { total_copies: 'Must be a whole number.' });
 */
export class ApiError extends Error {
  readonly fieldErrors: FieldErrors;

  constructor(message: string, fieldErrors: FieldErrors = {}) {
    super(message);
    this.fieldErrors = fieldErrors;
  }
}

/**
 * User-facing text for the server's `detail` codes. Each feature adds its codes
 * here so every form shows the same wording for the same refusal.
 */
const ERROR_MESSAGES: Record<string, string> = {
  LOGIN_BAD_CREDENTIALS: 'Incorrect email or password.',
  REGISTER_USER_ALREADY_EXISTS: 'An account already exists for this email.',
  LOAN_BOOK_NOT_FOUND: 'That book is no longer in the catalogue.',
  LOAN_BORROWER_NOT_FOUND: 'No active member account has that email.',
  LOAN_NO_COPIES_AVAILABLE: 'Every copy of that book is already on loan.',
  LOAN_ALREADY_BORROWED: 'That member already has this book on loan.',
  LOAN_NOT_FOUND: 'That loan no longer exists.',
  LOAN_ALREADY_RETURNED: 'That loan has already been checked in.',
  MEMBER_NOT_FOUND: 'That member account no longer exists.',
  STAFF_NOT_FOUND: 'That librarian account no longer exists.',
  CATALOG_DUPLICATE_ISBN: 'A book with this ISBN already exists.',
  CATALOG_BOOK_NOT_FOUND: 'That book is no longer in the catalogue.',
  CATALOG_BOOK_ON_LOAN: 'Check in all copies before removing this book.',
  CATALOG_TOO_FEW_COPIES: 'Copies cannot be fewer than the number currently on loan.',
};

/**
 * Refusal codes that are about one input, so forms show them beside it. The
 * field names are the API's, which every form uses for its inline errors.
 */
const ERROR_FIELDS: Record<string, string> = {
  REGISTER_USER_ALREADY_EXISTS: 'email',
  LOAN_BOOK_NOT_FOUND: 'book_id',
  LOAN_BORROWER_NOT_FOUND: 'borrower_email',
  LOAN_NO_COPIES_AVAILABLE: 'book_id',
  LOAN_ALREADY_BORROWED: 'book_id',
  CATALOG_DUPLICATE_ISBN: 'isbn',
  CATALOG_TOO_FEW_COPIES: 'total_copies',
};

/** Reads the server's `VALIDATION_FAILED` body: `errors: [{field, message}]`. */
function validationError(errors: unknown, fallback: string): ApiError {
  if (!Array.isArray(errors)) return new ApiError(fallback);
  const fieldErrors: Record<string, string> = {};
  const general: string[] = [];
  for (const error of errors) {
    if (typeof error?.message !== 'string') continue;
    if (typeof error.field === 'string') fieldErrors[error.field] ??= error.message;
    else general.push(error.message);
  }
  if (general.length === 0 && Object.keys(fieldErrors).length === 0) return new ApiError(fallback);
  return new ApiError(general.join(' '), fieldErrors);
}

async function errorFrom(res: Response, fallback: string): Promise<ApiError> {
  const body = await res.json().catch(() => null);
  const detail = body?.detail;
  if (detail === 'VALIDATION_FAILED') return validationError(body.errors, fallback);
  if (typeof detail === 'string') {
    const message = ERROR_MESSAGES[detail];
    if (message === undefined) return new ApiError(fallback);
    const field = ERROR_FIELDS[detail];
    return field === undefined ? new ApiError(message) : new ApiError('', { [field]: message });
  }
  if (detail?.code === 'REGISTER_INVALID_PASSWORD' && typeof detail.reason === 'string') {
    return new ApiError('', { password: detail.reason });
  }
  return new ApiError(fallback);
}

/**
 * `fetch`, but a request that never got a response (offline, server down)
 * throws `ApiError` so forms show it instead of failing silently.
 *
 *     const res = await reach('/api/auth/logout', { method: 'POST' });
 */
export async function reach(path: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(path, init);
  } catch {
    throw new ApiError('Could not reach the server. Check your connection and try again.');
  }
}

/** Request options for a JSON body. */
export function jsonBody(method: 'POST' | 'PATCH', body: unknown): RequestInit {
  return { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) };
}

/**
 * Sends a user action; throws `ApiError` (with `fallback` when the server gave
 * no known code) if the server refuses it.
 *
 *     await send('/api/auth/logout', { method: 'POST' }, 'Logout failed.');
 */
export async function send(path: string, init: RequestInit, fallback: string): Promise<Response> {
  const res = await reach(path, init);
  if (!res.ok) throw await errorFrom(res, fallback);
  return res;
}

/**
 * Loads data for a page; throws a plain `Error` naming the request on failure.
 *
 *     const page = await getJson<BookPage>('/api/books?limit=50');
 */
export async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`GET ${path} failed with ${res.status}`);
  return res.json();
}
