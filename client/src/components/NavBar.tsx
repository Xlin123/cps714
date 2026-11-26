import { Link, NavLink } from 'react-router-dom';
import type { Capability } from '../auth/api';
import { useAuth } from '../auth/useAuth';
import { useSubmit } from '../hooks/useSubmit';
import { useReminders } from '../lending/useReminders';

/**
 * The "My loans" link with its status badge: red count if anything is overdue,
 * amber count if loans are only due soon, green check when nothing needs attention.
 * No badge until reminders load, so a failed request never claims "all clear".
 */
function MyLoansLink() {
  const { reminders, isLoaded } = useReminders();
  const count = reminders.length;

  if (!isLoaded) return <NavLink to="/history">My loans</NavLink>;
  if (count === 0) {
    return (
      <NavLink to="/history" aria-label="My loans, nothing due soon">
        My loans
        <span className="nav-badge clear">✓</span>
      </NavLink>
    );
  }
  const isAnyOverdue = reminders.some((loan) => loan.reminder === 'overdue');
  return (
    <NavLink to="/history" aria-label={`My loans, ${count} need attention`}>
      My loans
      <span className={isAnyOverdue ? 'nav-badge overdue' : 'nav-badge'}>{count}</span>
    </NavLink>
  );
}

export function NavBar() {
  const { user, logout } = useAuth();
  const signOut = useSubmit(logout);
  const can = (capability: Capability) => user?.capabilities.includes(capability) ?? false;

  return (
    <nav className="navbar">
      <div className="navbar-links">
        <NavLink to="/" end>
          Catalogue
        </NavLink>
        {can('view_own_loans') && <MyLoansLink />}
        {can('view_dashboard') && <NavLink to="/dashboard">Dashboard</NavLink>}
        {can('lend_books') && <NavLink to="/staff">Lending</NavLink>}
        {can('view_members') && <NavLink to="/members">Members</NavLink>}
        {can('manage_staff') && <NavLink to="/admin">Staff accounts</NavLink>}
        {can('view_reports') && <NavLink to="/reports">Reports</NavLink>}
      </div>
      <div className="navbar-account">
        {user ? (
          <>
            <span>
              {user.name} ({user.role})
            </span>
            <button onClick={signOut.onSubmit} disabled={signOut.submitting}>
              Log out
            </button>
            {signOut.error && (
              <span className="error" role="alert">
                {signOut.error}
              </span>
            )}
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
