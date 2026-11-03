/** A request the server refused, with a message safe to show the user. */
export class ApiError extends Error {}

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
};

async function errorFrom(res: Response, fallback: string): Promise<ApiError> {
  const body = await res.json().catch(() => null);
  const detail = body?.detail;
  if (typeof detail === 'string') return new ApiError(ERROR_MESSAGES[detail] ?? fallback);
  if (detail?.code === 'REGISTER_INVALID_PASSWORD' && typeof detail.reason === 'string') {
    return new ApiError(detail.reason);
  }
  return new ApiError(fallback);
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
  const res = await fetch(path, init);
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
