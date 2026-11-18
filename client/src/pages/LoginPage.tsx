import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../auth/useAuth';
import { FieldError } from '../components/FieldError';
import { invalidProps } from '../components/invalidProps';
import { DemoAccountButtons } from './DemoAccountButtons';
import { useSubmit } from '../hooks/useSubmit';

export function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const { error, fieldErrors, submitting, onSubmit } = useSubmit(
    () => login(email, password),
    ['username', 'password'],
  );

  return (
    <div className="page">
      <h1>Log in</h1>
      <DemoAccountButtons
        onPick={(account) => {
          setEmail(account.email);
          setPassword(account.password);
        }}
      />
      <form onSubmit={onSubmit}>
        <label htmlFor="email">Email</label>
        <input
          id="email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          {...invalidProps('email', fieldErrors.username)}
        />
        <FieldError inputId="email" message={fieldErrors.username} />
        <label htmlFor="password">Password</label>
        <input
          id="password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          {...invalidProps('password', fieldErrors.password)}
        />
        <FieldError inputId="password" message={fieldErrors.password} />
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={submitting}>
          {submitting ? 'Logging in…' : 'Log in'}
        </button>
      </form>
      <p>
        No account? <Link to="/register">Register</Link>
      </p>
    </div>
  );
}
