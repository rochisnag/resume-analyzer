import { useState } from "react";
import tektalisLogo from "../assets/tektalis-logo.svg";

const API_BASE = "http://localhost:8000";

export default function SignInPage({ onSignedIn }) {
  const [credentials, setCredentials] = useState({ email: "", password: "" });
  const [forgotMode, setForgotMode] = useState(false);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);

  const signIn = async (event) => {
    event.preventDefault();
    setBusy(true);
    setStatus("");
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(credentials),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setStatus(data.detail || "Unable to sign in");
        return;
      }
      onSignedIn(data.user);
    } catch {
      setStatus("Unable to reach the backend");
    } finally {
      setBusy(false);
    }
  };

  const resetPassword = async (event) => {
    event.preventDefault();
    setBusy(true);
    setStatus("");
    try {
      const res = await fetch(`${API_BASE}/auth/forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: credentials.email }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setStatus(data.detail || "Unable to reset password");
        return;
      }
      setStatus(data.message || "Check your email for the new temporary password");
      setForgotMode(false);
      setCredentials({ ...credentials, password: "" });
    } catch {
      setStatus("Unable to reach the backend");
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="signin-page">
      <section className="signin-panel">
        <div className="signin-brand">
          <span className="signin-logo-surface">
            <img src={tektalisLogo} alt="Tektalis" className="signin-logo" />
          </span>
          <div>
            <span className="eyebrow">Resume Analyzer</span>
            <h1>{forgotMode ? "Reset password" : "Sign in"}</h1>
          </div>
        </div>

        <form className="signin-form" onSubmit={forgotMode ? resetPassword : signIn}>
          <label>
            <span>Email / ID</span>
            <input
              type="text"
              autoComplete="username"
              value={credentials.email}
              onChange={(event) => setCredentials({ ...credentials, email: event.target.value })}
              required
            />
          </label>
          {!forgotMode && (
            <label>
              <span>Password</span>
              <input
                type="password"
                autoComplete="current-password"
                value={credentials.password}
                onChange={(event) => setCredentials({ ...credentials, password: event.target.value })}
                required
              />
            </label>
          )}
          <button className="primary-action" type="submit" disabled={busy}>
            {busy ? "Working..." : forgotMode ? "Reset password" : "Sign in"}
          </button>
          <button
            className="signin-link"
            type="button"
            onClick={() => {
              setForgotMode(!forgotMode);
              setStatus("");
            }}
          >
            {forgotMode ? "Back to sign in" : "Forgot password?"}
          </button>
          {status && <p className="signin-status">{status}</p>}
        </form>
      </section>
    </main>
  );
}
