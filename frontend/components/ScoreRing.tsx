interface ScoreRingProps {
  score: number;
  color: string;
  label: string;
}

export function ScoreRing({ score, color, label }: ScoreRingProps) {
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div className="score-ring-wrap">
      <svg className="score-ring" viewBox="0 0 128 128" aria-hidden="true">
        <circle
          className="score-ring-bg"
          cx="64"
          cy="64"
          r={radius}
          fill="none"
          strokeWidth="10"
        />
        <circle
          className="score-ring-fill"
          cx="64"
          cy="64"
          r={radius}
          fill="none"
          strokeWidth="10"
          stroke={color}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform="rotate(-90 64 64)"
        />
      </svg>
      <div className="score-ring-content">
        <span className="score-ring-value" style={{ color }}>
          {score}%
        </span>
        <span className="score-ring-label">{label}</span>
      </div>
    </div>
  );
}
