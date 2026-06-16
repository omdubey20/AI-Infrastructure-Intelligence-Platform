import React from "react";

const THEMES = {
  blue:   { accent: "#38BDF8", bg: "rgba(56,189,248,0.07)",  border: "rgba(56,189,248,0.18)"  },
  green:  { accent: "#22C55E", bg: "rgba(34,197,94,0.07)",   border: "rgba(34,197,94,0.18)"   },
  amber:  { accent: "#F59E0B", bg: "rgba(245,158,11,0.07)",  border: "rgba(245,158,11,0.18)"  },
  red:    { accent: "#F87171", bg: "rgba(248,113,113,0.07)", border: "rgba(248,113,113,0.18)" },
  teal:   { accent: "#2DD4BF", bg: "rgba(45,212,191,0.07)",  border: "rgba(45,212,191,0.18)"  },
};

export default function StatCard({ title, value, icon, color = "blue", subtitle }) {
  const t = THEMES[color] || THEMES.blue;
  return (
    <div className="animate-fadein" style={{
      background: "#111c2e",
      border: `1px solid ${t.border}`,
      borderRadius: "12px", padding: "20px 22px",
      transition: "transform 0.15s, border-color 0.2s",
      cursor: "default",
    }}
      onMouseEnter={e => e.currentTarget.style.transform = "translateY(-2px)"}
      onMouseLeave={e => e.currentTarget.style.transform = "translateY(0)"}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "12px" }}>
        <p style={{ fontSize: "11px", fontWeight: 700, color: "#64748b",
          letterSpacing: "0.1em", textTransform: "uppercase" }}>{title}</p>
        {icon && (
          <div style={{ width: "30px", height: "30px", borderRadius: "8px",
            background: t.bg, display: "flex", alignItems: "center",
            justifyContent: "center", fontSize: "15px" }}>{icon}</div>
        )}
      </div>
      <p style={{ fontSize: "32px", fontWeight: 800, color: t.accent, lineHeight: 1, marginBottom: subtitle ? "6px" : 0 }}>
        {value ?? "—"}
      </p>
      {subtitle && (
        <p style={{ fontSize: "12px", color: "#64748b", marginTop: "4px" }}>{subtitle}</p>
      )}
    </div>
  );
}