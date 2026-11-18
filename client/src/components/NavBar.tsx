import { Link, NavLink } from 'react-router-dom';
import type { Capability } from '../auth/api';
import { useAuth } from '../auth/useAuth';
import { useReminders } from '../lending/useReminders';

export function NavBar() {
  const { user, logout } = useAuth();
  const { reminders } = useReminders();
  const can = (capability: Capability) => user?.capabilities.includes(capability) ?? false;
  const count = reminders.length;
  const isAnyOverdue = reminders.some((loan) => loan.reminder === 'overdue');

  return (
    <nav className="navbar">
      <div className="navbar-links">
        <NavLink to="/" end>
          Catalogue
        </NavLink>
        {can('view_own_loans') && (
          <NavLink
            to="/history"
            aria-label={count > 0 ? `My loans, ${count} need attention` : undefined}
          >
            My loans
            {count > 0 && (
              <span className={isAnyOverdue ? 'nav-badge overdue' : 'nav-badge'}>{count}</span>
            )}
          </NavLink>
        )}
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
