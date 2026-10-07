import { Navigate, Route, Routes } from 'react-router-dom';
import { useAuth } from './auth/useAuth';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { HomePage } from './pages/HomePage';
import './App.css';

function RequireUser({ children }: { children: React.ReactNode }) {
  const { loading, loadError, user } = useAuth();

  if (loading) return <div className="page">Loading…</div>;
  if (loadError) return <div className="page error">Could not reach the server: {loadError}</div>;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function GuestOnly({ children }: { children: React.ReactNode }) {
  const { loading, loadError, user } = useAuth();

  if (loading) return <div className="page">Loading…</div>;
  if (loadError) return <div className="page error">Could not reach the server: {loadError}</div>;
  if (user) return <Navigate to="/" replace />;
  return <>{children}</>;
}

function App() {
  return (
    <Routes>
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
        path="/"
        element={
          <RequireUser>
            <HomePage />
          </RequireUser>
        }
      />
    </Routes>
  );
}

export default App;
