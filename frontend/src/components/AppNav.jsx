export default function AppNav({ active, onNavigate, rightSlot }) {
  const items = [
    ["configure", "Configure"],
    ["upload", "Upload"],
    ["list", "Leaderboard"],
    ["users", "Users"],
  ];

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
