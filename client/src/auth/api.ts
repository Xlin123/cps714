import { jsonBody, send } from '../api/http';

export type Role = 'member' | 'librarian' | 'admin';

/** Mirrors the server's Capability enum; the server decides who holds which. */
export type Capability = 'lend_books' | 'manage_staff' | 'manage_catalog';

export interface SessionUser {
  id: string;
  name: string;
  email: string;
  role: Role;
  capabilities: Capability[];
}

export interface RegisterInput {
  name: string;
  email: string;
  password: string;
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
  await send(
    '/api/auth/login',
    { method: 'POST', body: new URLSearchParams({ username: email, password }) },
    'Login failed.',
  );
}

export async function register(input: RegisterInput): Promise<void> {
  await send('/api/auth/register', jsonBody('POST', input), 'Registration failed.');
}

export async function logout(): Promise<void> {
  const res = await fetch('/api/auth/logout', { method: 'POST' });
  // 401 means the session had already expired, which is the state we want.
  if (!res.ok && res.status !== 401) throw new Error(`Logout failed with ${res.status}`);
}

export interface DemoAccount {
  role: Role;
  email: string;
  password: string;
}

/** Demo logins, or an empty list when the server has them switched off. */
export async function fetchDemoAccounts(): Promise<DemoAccount[]> {
  const res = await fetch('/api/dev/demo-accounts');
  if (res.status === 404) return [];
  if (!res.ok) throw new Error(`GET /api/dev/demo-accounts failed with ${res.status}`);
  return res.json();
}
