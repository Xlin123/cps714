import { createContext, useContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';

export type Role = 'member' | 'librarian' | 'admin';

export interface SessionUser {
  name: string;
  email: string;
  role: Role;
}

interface SessionResponse {
  needsRegistration: boolean;
  email?: string;
  user?: SessionUser;
}

interface AuthState {
  loading: boolean;
  /** Whether oauth2-proxy has an authenticated Google session for this browser. */
  googleAuthed: boolean;
  user: SessionUser | null;
  needsRegistration: boolean;
  pendingEmail: string | null;
  refresh: () => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [googleAuthed, setGoogleAuthed] = useState(false);
  const [user, setUser] = useState<SessionUser | null>(null);
  const [needsRegistration, setNeedsRegistration] = useState(false);
  const [pendingEmail, setPendingEmail] = useState<string | null>(null);

  async function refresh() {
    setLoading(true);
    try {
      // oauth2-proxy's built-in forward-auth endpoint: 202/200 if signed in,
      // 401 if not. It never redirects, so it's safe to call while logged out.
      const authRes = await fetch('/oauth2/auth');
      if (!authRes.ok) {
        setGoogleAuthed(false);
        setUser(null);
        setNeedsRegistration(false);
        setPendingEmail(null);
        return;
      }
      setGoogleAuthed(true);

      // Cookie is valid at this point, so oauth2-proxy will pass this straight
      // through to the app instead of redirecting.
      const res = await fetch('/api/auth/session');
      const data: SessionResponse = await res.json();
      if (data.needsRegistration) {
        setUser(null);
        setNeedsRegistration(true);
        setPendingEmail(data.email ?? null);
      } else {
        setUser(data.user ?? null);
        setNeedsRegistration(false);
        setPendingEmail(null);
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  function logout() {
    window.location.href = '/oauth2/sign_out';
  }

  return (
    <AuthContext.Provider
      value={{ loading, googleAuthed, user, needsRegistration, pendingEmail, refresh, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
}
