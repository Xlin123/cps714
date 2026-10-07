import { useAuth } from '../auth/useAuth';

export function HomePage() {
  const { user, logout } = useAuth();

  return (
    <div className="page">
      <h1>Library Management System</h1>
      {user && (
        <>
          <p>
            Welcome, {user.name} ({user.role}).
          </p>
          <button onClick={logout}>Log out</button>
        </>
      )}
    </div>
  );
}
