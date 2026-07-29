import React from "react";

const SEVERITY_CONFIG = {
  critical: { bg: "rgba(248,113,113,0.08)", border: "rgba(248,113,113,0.25)", text: "#f87171", icon: "🚨" },
  warning:  { bg: "rgba(245,158,11,0.08)",  border: "rgba(245,158,11,0.25)",  text: "#fbbf24", icon: "⚠️" },
  info:     { bg: "rgba(56,189,248,0.08)",  border: "rgba(56,189,248,0.25)",  text: "#38bdf8", icon: "💡" },
};

export default function AIInsightCard({ title, description, recommendation, severity = "info", category }) {
  const cfg = SEVERITY_CONFIG[severity] || SEVERITY_CONFIG.info;

  return (
    <div className="card" style={{
      background: cfg.bg,
      border: `1px solid ${cfg.border}`,
      marginBottom: "12px",
      padding: "16px 20px"
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "6px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span>{cfg.icon}</span>
          <h4 style={{ color: "#f1f5f9", fontWeight: 700, fontSize: "14px" }}>{title}</h4>
        </div>
        {category && (
          <span style={{ fontSize: "10px", fontWeight: 800, color: cfg.text, letterSpacing: "0.08em", textTransform: "uppercase", background: "rgba(15,23,42,0.6)", padding: "2px 8px", borderRadius: "4px" }}>
            {category}
          </span>
        )}
      </div>
      <p style={{ color: "#94a3b8", fontSize: "13px", marginBottom: recommendation ? "8px" : 0 }}>
        {description}
      </p>
      {recommendation && (
        <div style={{ fontSize: "12px", color: cfg.text, fontWeight: 600, background: "rgba(0,0,0,0.2)", padding: "8px 12px", borderRadius: "6px" }}>
          👉 Recommendation: {recommendation}
        </div>
      )}
    </div>
  );
}
