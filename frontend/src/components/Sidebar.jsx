import React from "react";
import { NavLink, useNavigate } from "react-router-dom";

export default function Sidebar() {
  const navigate = useNavigate();
  const handleLogout = () => {
    localStorage.removeItem("token");
    navigate("/login");
  };

  const navItems = [
    { path: "/dashboard", label: "Dashboard", icon: "📊" },
    { path: "/servers", label: "Servers", icon: "🖥️" },
    { path: "/projects", label: "Projects", icon: "📁" },
    { path: "/cleanup", label: "Cleanup", icon: "🧹" },
  ];

  return (
    <aside style={{
      width: "240px", minHeight: "100vh", background: "#0f172a",
      display: "flex", flexDirection: "column",
      borderRight: "1px solid #1e293b", flexShrink: 0
    }}>
      {/* Logo */}
      <div style={{ padding: "28px 24px 20px", borderBottom: "1px solid #1e293b" }}>
        <div style={{
          width: "40px", height: "40px", borderRadius: "10px",
          background: "linear-gradient(135deg, #0ea5e9, #6366f1)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: "18px", fontWeight: 800, color: "#fff", marginBottom: "12px"
        }}>A</div>
        <div style={{ fontSize: "16px", fontWeight: 800, color: "#f1f5f9", letterSpacing: "0.3px" }}>
          Infra Intel
        </div>
        <div style={{ fontSize: "11px", color: "#64748b", letterSpacing: "1.5px", marginTop: "2px" }}>
          AI PLATFORM
        </div>
      </div>

      {/* Nav */}
      <div style={{ padding: "8px 0", flex: 1 }}>
        <div style={{ padding: "12px 24px 6px", fontSize: "10px", color: "#475569", letterSpacing: "1.5px", fontWeight: 700 }}>
          NAVIGATION
        </div>
        {navItems.map(({ path, label, icon }) => (
          <NavLink key={path} to={path} style={({ isActive }) => ({
            display: "flex", alignItems: "center", gap: "10px",
            padding: "10px 24px", textDecoration: "none",
            color: isActive ? "#38bdf8" : "#94a3b8",
            background: isActive ? "#1e293b" : "transparent",
            borderLeft: isActive ? "3px solid #38bdf8" : "3px solid transparent",
            fontWeight: isActive ? 600 : 400, fontSize: "14px",
            transition: "all 0.15s"
          })}>
            <span>{icon}</span><span>{label}</span>
          </NavLink>
        ))}
      </div>

      {/* Logout */}
      <div style={{ padding: "16px 24px", borderTop: "1px solid #1e293b" }}>
        <button onClick={handleLogout} style={{
          display: "flex", alignItems: "center", gap: "8px",
          background: "none", border: "none", color: "#64748b",
          cursor: "pointer", fontSize: "13px", padding: "0"
        }}>
          <span>↩</span><span>Sign Out</span>
        </button>
        <div style={{ fontSize: "10px", color: "#334155", marginTop: "10px" }}>
          v1.0.0 · AI-IIP
        </div>
      </div>
    </aside>
  );
}
