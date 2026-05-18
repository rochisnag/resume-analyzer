export default function AppNav({ active, onNavigate, rightSlot, currentUser }) {
  const canManageUsers = currentUser?.role === "admin";
  const items = [
    ["configure", "Configure"],
    ["upload", "Upload"],
    ["list", "Leaderboard"],
    canManageUsers ? ["users", "Users"] : null,
  ].filter(Boolean);

  return (
    <nav className="leaderboard-nav" aria-label="ResumeEval sections">
      {items.map(([key, label]) => (
        <button
          key={key}
          type="button"
          className={active === key ? "active" : ""}
          onClick={() => onNavigate(key)}
        >
          {label}
        </button>
      ))}
      {rightSlot && <div className="nav-actions">{rightSlot}</div>}
    </nav>
  );
}
