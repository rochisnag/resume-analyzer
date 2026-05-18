export default function ScoreRing({ score, label, color, size = 100 }) {
  const r = size * 0.38;
  const cx = size / 2;
  const circ = 2 * Math.PI * r;
  const fill = circ * (1 - score / 100);

  const getGrade = (s) => {
    if (s >= 85) return "A";
    if (s >= 70) return "B";
    if (s >= 55) return "C";
    if (s >= 40) return "D";
    return "F";
  };

  return (
    <div className="score-ring-wrap">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {/* Background track */}
        <circle
          cx={cx} cy={cx} r={r}
          fill="none"
          stroke="rgba(255,255,255,0.08)"
          strokeWidth={size * 0.08}
        />
        {/* Progress arc */}
        <circle
          cx={cx} cy={cx} r={r}
          fill="none"
          stroke={color}
          strokeWidth={size * 0.08}
          strokeDasharray={circ}
          strokeDashoffset={fill}
          strokeLinecap="round"
          transform={`rotate(-90 ${cx} ${cx})`}
          style={{ transition: "stroke-dashoffset 1s ease" }}
        />
        {/* Score number */}
        <text
          x={cx} y={cx - size * 0.04}
          textAnchor="middle"
          dominantBaseline="central"
          fontSize={size * 0.22}
          fontWeight="700"
          fill={color}
          fontFamily="'DM Mono', monospace"
        >
          {score}
        </text>
        {/* Grade */}
        <text
          x={cx} y={cx + size * 0.2}
          textAnchor="middle"
          dominantBaseline="central"
          fontSize={size * 0.13}
          fill="rgba(255,255,255,0.45)"
          fontFamily="'DM Mono', monospace"
        >
          {getGrade(score)}
        </text>
      </svg>
      <p className="ring-label">{label}</p>
    </div>
  );
}
