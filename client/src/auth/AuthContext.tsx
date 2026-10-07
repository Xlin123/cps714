import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import * as api from './api';
import type { RegisterInput, SessionUser } from './api';
import { AuthContext } from './useAuth';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [user, setUser] = useState<SessionUser | null>(null);

  useEffect(() => {
    let isCancelled = false;
    api
      .fetchMe()
      .then((me) => {
        if (!isCancelled) setUser(me);
      })
      .catch((err: unknown) => {
        if (!isCancelled) setLoadError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (!isCancelled) setLoading(false);
      });
    return () => {
      isCancelled = true;
    };
  }, []);

  async function login(email: string, password: string) {
    await api.login(email, password);
    setUser(await api.fetchMe());
  }

  async function register(input: RegisterInput) {
    await api.register(input);
    await login(input.email, input.password);
  }

  async function logout() {
    await api.logout();
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ loading, loadError, user, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
