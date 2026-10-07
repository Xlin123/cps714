import { Navigate, Route, Routes } from 'react-router-dom';
import type { ReactNode } from 'react';
import type { Capability } from './auth/api';
import { useAuth } from './auth/useAuth';
import { AreaPage } from './areas/AreaPage';
import { CatalogPage } from './catalog/CatalogPage';
import { NavBar } from './components/NavBar';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import './App.css';

/** Holds rendering until the session check settles, so guards see the real user. */
function SessionReady({ children }: { children: ReactNode }) {
  const { loading, loadError } = useAuth();

  if (loading) return <div className="page">Loading…</div>;
  if (loadError) return <div className="page error">Could not reach the server: {loadError}</div>;
  return <>{children}</>;
}

/**
 * Hides a page from roles without `capability`. The server enforces the same
 * rule on the page's data; this only spares users a page that would fail.
 */
function RequireCapability({
  capability,
  children,
}: {
  capability: Capability;
  children: ReactNode;
}) {
  const { user } = useAuth();

  if (!user) return <Navigate to="/login" replace />;
  if (!user.capabilities.includes(capability)) {
    return (
      <div className="page">
        <h1>No access</h1>
        <p>You don't have access to this page.</p>
      </div>
    );
  }
  return <>{children}</>;
}

function GuestOnly({ children }: { children: ReactNode }) {
  const { user } = useAuth();

  if (user) return <Navigate to="/" replace />;
  return <>{children}</>;
}

function App() {
  return (
    <SessionReady>
      <NavBar />
      <Routes>
        <Route path="/" element={<CatalogPage />} />
        <Route
          path="/login"
          element={
            <GuestOnly>
              <LoginPage />
            </GuestOnly>
          }
        />
        <Route
          path="/register"
          element={
            <GuestOnly>
              <RegisterPage />
            </GuestOnly>
          }
        />
        <Route
          path="/staff"
          element={
            <RequireCapability capability="view_staff_area">
              <AreaPage area="staff" />
            </RequireCapability>
          }
        />
        <Route
          path="/admin"
          element={
            <RequireCapability capability="view_admin_area">
              <AreaPage area="admin" />
            </RequireCapability>
          }
        />
        <Route
          path="*"
          element={
            <div className="page">
              <h1>Not found</h1>
            </div>
          }
        />
      </Routes>
    </SessionReady>
  );
}

export default App;
