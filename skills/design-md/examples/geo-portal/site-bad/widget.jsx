export function RiskBadge({ level }) {
  const palette = { low: "#00ff00", medium: "#FFD700", high: "#FF0000" };
  return (
    <span style={{ background: palette[level], fontFamily: "Inter, sans-serif", padding: 6 }}>
      {level}
    </span>
  );
}
