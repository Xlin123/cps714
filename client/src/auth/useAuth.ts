import { createContext, useContext } from 'react';
import type { RegisterInput, SessionUser } from './api';

export interface AuthState {
  loading: boolean;
  /** Set when the initial session check could not reach the server. */
  loadError: string | null;
  user: SessionUser | null;
  login: (email: string, password: string) => Promise<void>;
  register: (input: RegisterInput) => Promise<void>;
  logout: () => Promise<void>;
}

export const AuthContext = createContext<AuthState | undefined>(undefined);

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
}
