import { Navigate, Route, Routes } from 'react-router-dom';
import { useAuth } from './auth/AuthContext';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { HomePage } from './pages/HomePage';
import './App.css';

function Gate({ children }: { children: React.ReactNode }) {
  const { loading, googleAuthed, user, needsRegistration } = useAuth();

  if (loading) return <div className="page">Loading…</div>;
  if (!googleAuthed) return <Navigate to="/login" replace />;
  if (needsRegistration) return <Navigate to="/register" replace />;
  if (!user) return <div className="page">Loading…</div>;
  return <>{children}</>;
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        path="/"
        element={
          <Gate>
            <HomePage />
          </Gate>
        }
      />
    </Routes>
  );
}

export default App;
