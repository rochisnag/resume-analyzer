import { useState } from "react";
import AppNav from "./AppNav";

const API_BASE = "http://localhost:8000";

export default function AdminPage({ onNavigate }) {
  const [userDraft, setUserDraft] = useState({
    email: "",
    password: "",
    role: "recruiter",
  });
  const [userStatus, setUserStatus] = useState("");

  const createUser = async (event) => {
    event.preventDefault();
    setUserStatus("");
    const res = await fetch(`${API_BASE}/admin/users`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(userDraft),
    });
    if (!res.ok) {
      const error = await res.json().catch(() => ({}));
      setUserStatus(error.detail || "Unable to create user");
      return;
    }
    setUserDraft({ email: "", password: "", role: "recruiter" });
    setUserStatus("User created");
  };

  return (
    <div className="leaderboard-page">
      <div className="leaderboard-shell configure-shell">
        <AppNav
          active="users"
          onNavigate={onNavigate}
          rightSlot={<span className="admin-pill">Access</span>}
        />

        <section className="admin-grid full-page">
          <form className="admin-panel" onSubmit={createUser}>
            <div>
              <span className="eyebrow">Access</span>
              <h2>Create resume analyzer user</h2>
            </div>
            <label>
              <span>Username</span>
              <input
                type="text"
                autoComplete="username"
                value={userDraft.email}
                onChange={(event) => setUserDraft({ ...userDraft, email: event.target.value })}
                required
              />
            </label>
            <label>
              <span>Password</span>
              <input
                type="password"
                minLength={8}
                value={userDraft.password}
                onChange={(event) => setUserDraft({ ...userDraft, password: event.target.value })}
                required
              />
            </label>
            <label>
              <span>Role</span>
              <select
                value={userDraft.role}
                onChange={(event) => setUserDraft({ ...userDraft, role: event.target.value })}
              >
                <option value="recruiter">Recruiter</option>
                <option value="admin">Admin</option>
              </select>
            </label>
            <button className="primary-action" type="submit">Create user</button>
            {userStatus && <p className="admin-status">{userStatus}</p>}
          </form>

          <aside className="admin-side-panel">
            <section>
              <span className="eyebrow">Permissions</span>
              <h2>Role access</h2>
              <div className="access-role-list">
                <article>
                  <strong>Recruiter</strong>
                  <span>Can upload resumes, run analysis, and review the leaderboard.</span>
                </article>
                <article>
                  <strong>Admin</strong>
                  <span>Can create users and manage mail configuration for resume workflows.</span>
                </article>
              </div>
            </section>

            <section>
              <span className="eyebrow">Current setup</span>
              <div className="access-stat-grid">
                <div>
                  <strong>2</strong>
                  <span>Available roles</span>
                </div>
                <div>
                  <strong>8+</strong>
                  <span>Password characters</span>
                </div>
              </div>
            </section>
          </aside>
        </section>
      </div>
    </div>
  );
}
