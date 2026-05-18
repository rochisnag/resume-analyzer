import { useState } from "react";
import tektalisLogo from "../assets/tektalis-logo.svg";

const API_BASE = "http://127.0.0.1:8000";

export default function SignInPage({ onSignedIn }) {
  const [credentials, setCredentials] = useState({ email: "", password: "" });
  const [setupMode, setSetupMode] = useState(false);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);

  const signIn = async (event) => {
    event.preventDefault();
    if (setupMode) {
      await createFirstAdmin();
      return;
    }
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

  const createFirstAdmin = async () => {
    setBusy(true);
    setStatus("");
    try {
      const res = await fetch(`${API_BASE}/auth/bootstrap`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...credentials, role: "admin" }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setStatus(data.detail || "Unable to create first admin");
        return;
      }
      onSignedIn(data.user);
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
            <h1>{setupMode ? "Create first admin" : "Sign in"}</h1>
          </div>
        </div>

        <form className="signin-form" onSubmit={signIn}>
          <label>
            <span>Email</span>
            <input
              type="email"
              autoComplete="email"
              value={credentials.email}
              onChange={(event) => setCredentials({ ...credentials, email: event.target.value })}
              required
            />
          </label>
          <label>
            <span>Password</span>
            <input
              type="password"
              autoComplete="current-password"
              minLength={setupMode ? 8 : undefined}
              value={credentials.password}
              onChange={(event) => setCredentials({ ...credentials, password: event.target.value })}
              required
            />
          </label>
          <button
            className="primary-action"
            type={setupMode ? "button" : "submit"}
            disabled={busy}
            onClick={setupMode ? createFirstAdmin : undefined}
          >
            {busy ? "Working..." : setupMode ? "Create admin" : "Sign in"}
          </button>
          <button
            className="signin-link"
            type="button"
            onClick={() => {
              setSetupMode(!setupMode);
              setStatus("");
            }}
          >
            {setupMode ? "Back to sign in" : "First time setup"}
          </button>
          {status && <p className="signin-status">{status}</p>}
        </form>
      </section>
    </main>
  );
}
