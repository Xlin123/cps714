import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../auth/useAuth';
import { FieldError } from '../components/FieldError';
import { invalidProps } from '../components/invalidProps';
import { useSubmit } from '../hooks/useSubmit';

export function RegisterPage() {
  const { register } = useAuth();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const { error, fieldErrors, submitting, onSubmit } = useSubmit(
    () => register({ name, email, password }),
    ['name', 'email', 'password'],
  );

  return (
    <div className="page">
      <h1>Register</h1>
      <p>Create a member account.</p>
      <form onSubmit={onSubmit}>
        <label htmlFor="name">Name</label>
        <input
          id="name"
          autoComplete="name"
          maxLength={100}
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          {...invalidProps('name', fieldErrors.name)}
        />
        <FieldError inputId="name" message={fieldErrors.name} />
        <label htmlFor="email">Email</label>
        <input
          id="email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          {...invalidProps('email', fieldErrors.email)}
        />
        <FieldError inputId="email" message={fieldErrors.email} />
        <label htmlFor="password">Password</label>
        <input
          id="password"
          type="password"
          autoComplete="new-password"
          minLength={8}
          maxLength={128}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          {...invalidProps('password', fieldErrors.password)}
        />
        <FieldError inputId="password" message={fieldErrors.password} />
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={submitting}>
          {submitting ? 'Creating account…' : 'Create account'}
        </button>
      </form>
      <p>
        Already registered? <Link to="/login">Log in</Link>
      </p>
    </div>
  );
}
