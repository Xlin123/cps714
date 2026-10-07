export type Role = 'member' | 'librarian' | 'admin';

export interface SessionUser {
  id: string;
  name: string;
  email: string;
  role: Role;
}

export interface RegisterInput {
  name: string;
  email: string;
  password: string;
}

/** A request the server refused, with a message safe to show the user. */
export class AuthError extends Error {}

const ERROR_MESSAGES: Record<string, string> = {
  LOGIN_BAD_CREDENTIALS: 'Incorrect email or password.',
  REGISTER_USER_ALREADY_EXISTS: 'An account already exists for this email.',
};

async function errorFrom(res: Response, fallback: string): Promise<AuthError> {
  const body = await res.json().catch(() => null);
  const detail = body?.detail;
  if (typeof detail === 'string') return new AuthError(ERROR_MESSAGES[detail] ?? fallback);
  if (detail?.code === 'REGISTER_INVALID_PASSWORD' && typeof detail.reason === 'string') {
    return new AuthError(detail.reason);
  }
  return new AuthError(fallback);
}

/** Returns the signed-in user, or null when there is no valid session. */
export async function fetchMe(): Promise<SessionUser | null> {
  const res = await fetch('/api/auth/me');
  if (res.status === 401) return null;
  if (!res.ok) throw new Error(`GET /api/auth/me failed with ${res.status}`);
  return res.json();
}

export async function login(email: string, password: string): Promise<void> {
  // fastapi-users follows the OAuth2 password form: field names are fixed.
  const res = await fetch('/api/auth/login', {
    method: 'POST',
    body: new URLSearchParams({ username: email, password }),
  });
  if (!res.ok) throw await errorFrom(res, 'Login failed.');
}

export async function register(input: RegisterInput): Promise<void> {
  const res = await fetch('/api/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw await errorFrom(res, 'Registration failed.');
}

export async function logout(): Promise<void> {
  const res = await fetch('/api/auth/logout', { method: 'POST' });
  // 401 means the session had already expired, which is the state we want.
  if (!res.ok && res.status !== 401) throw new Error(`Logout failed with ${res.status}`);
}
