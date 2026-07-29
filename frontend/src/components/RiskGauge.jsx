import React from "react";

export default function RiskGauge({ score = 0, size = 64 }) {
  const s = Math.min(100, Math.max(0, Number(score) || 0));
  const color = s >= 70 ? "#f87171" : s >= 40 ? "#fbbf24" : "#4ade80";

  return (
    <div style={{ display: "inline-flex", flexDirection: "column", alignItems: "center" }}>
      <div style={{
        width: `${size}px`,
        height: `${size}px`,
        borderRadius: "50%",
        border: `4px solid ${color}`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontWeight: 800,
        fontSize: size > 60 ? "18px" : "14px",
        color: color,
        background: "rgba(17,28,46,0.6)"
      }}>
        {s}
      </div>
      <span style={{ fontSize: "10px", color: "#64748b", fontWeight: 700, marginTop: "4px", textTransform: "uppercase" }}>
        Risk
      </span>
    </div>
  );
}
