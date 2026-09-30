export function LoginPage() {
  return (
    <div className="page">
      <h1>Log in</h1>
      <p>Sign in with your Google account to access the library.</p>
      <a className="button" href="/oauth2/start">
        Sign in with Google
      </a>
    </div>
  );
}
