import { Link, NavLink } from 'react-router-dom';
import type { Capability } from '../auth/api';
import { useAuth } from '../auth/useAuth';

export function NavBar() {
  const { user, logout } = useAuth();
  const can = (capability: Capability) => user?.capabilities.includes(capability) ?? false;

  return (
    <nav className="navbar">
      <div className="navbar-links">
        <NavLink to="/" end>
          Catalogue
        </NavLink>
        {can('view_own_loans') && <NavLink to="/history">My loans</NavLink>}
        {can('lend_books') && <NavLink to="/staff">Lending</NavLink>}
        {can('manage_staff') && <NavLink to="/admin">Staff accounts</NavLink>}
      </div>
      <div className="navbar-account">
        {user ? (
          <>
            <span>
              {user.name} ({user.role})
            </span>
            <button onClick={logout}>Log out</button>
          </>
        ) : (
          <>
            <Link to="/login">Log in</Link>
            <Link to="/register">Register</Link>
          </>
        )}
      </div>
    </nav>
  );
}
