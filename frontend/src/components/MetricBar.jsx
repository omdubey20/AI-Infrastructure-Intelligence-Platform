import React from "react";

export default function MetricBar({ label, value = 0, unit = "%", thresholdWarning = 70, thresholdCritical = 85 }) {
  const v = Math.min(100, Math.max(0, Number(value) || 0));
  const color = v >= thresholdCritical ? "#f87171" : v >= thresholdWarning ? "#fbbf24" : "#38bdf8";

  return (
    <div style={{ marginBottom: "12px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", marginBottom: "4px" }}>
        <span style={{ color: "#94a3b8", fontWeight: 600 }}>{label}</span>
        <span style={{ color: color, fontWeight: 700 }}>{v}{unit}</span>
      </div>
      <div style={{ width: "100%", height: "6px", background: "#09111d", borderRadius: "999px", overflow: "hidden" }}>
        <div style={{ width: `${v}%`, height: "100%", background: color, borderRadius: "999px", transition: "width 0.4s ease" }} />
      </div>
    </div>
  );
}
