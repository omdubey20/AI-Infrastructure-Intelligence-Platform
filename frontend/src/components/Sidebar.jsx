import React from "react";
import { NavLink } from "react-router-dom";

const navItems = [
  { path: "/dashboard", label: "Dashboard", icon: "📊" },
  { path: "/servers", label: "Servers", icon: "🖥️" },
  { path: "/projects", label: "Projects", icon: "📁" },
  { path: "/cleanup", label: "Cleanup", icon: "🧹" },
];

export default function Sidebar() {
  return (
    <aside style={{
      width: "220px", minHeight: "100vh", background: "#0f172a",
      color: "#e2e8f0", display: "flex", flexDirection: "column",
      borderRight: "1px solid #1e293b"
    }}>
      <div style={{ padding: "24px 20px 16px", borderBottom: "1px solid #1e293b" }}>
        <div style={{ fontSize: "11px", color: "#64748b", letterSpacing: "2px", fontWeight: 700, marginBottom: "4px" }}>
          AI INFRASTRUCTURE
        </div>
        <div style={{ fontSize: "18px", fontWeight: 800, color: "#38bdf8" }}>
          Intelligence Platform
        </div>
      </div>
      <nav style={{ flex: 1, padding: "16px 0" }}>
        {navItems.map(({ path, label, icon }) => (
          <NavLink key={path} to={path} style={({ isActive }) => ({
            display: "flex", alignItems: "center", gap: "12px",
            padding: "11px 20px", textDecoration: "none",
            color: isActive ? "#38bdf8" : "#94a3b8",
            background: isActive ? "#1e293b" : "transparent",
            borderLeft: isActive ? "3px solid #38bdf8" : "3px solid transparent",
            fontWeight: isActive ? 700 : 400, fontSize: "14px"
          })}>
            <span>{icon}</span><span>{label}</span>
          </NavLink>
        ))}
      </nav>
      <div style={{ padding: "16px 20px", borderTop: "1px solid #1e293b", fontSize: "11px", color: "#475569" }}>
        v1.0.0 · AI-IIP
      </div>
    </aside>
  );
}
