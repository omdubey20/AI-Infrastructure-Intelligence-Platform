import React from "react";
import { NavLink, useNavigate } from "react-router-dom";

const DashboardIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
    <line x1="5" y1="20" x2="5" y2="13" />
    <line x1="12" y1="20" x2="12" y2="6" />
    <line x1="19" y1="20" x2="19" y2="16" />
  </svg>
);

const ServersIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="3" width="18" height="7" rx="1.5" />
    <rect x="3" y="14" width="18" height="7" rx="1.5" />
    <circle cx="7" cy="6.5" r="0.8" fill="currentColor" stroke="none" />
    <circle cx="7" cy="17.5" r="0.8" fill="currentColor" stroke="none" />
  </svg>
);

const ProjectsIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z" />
  </svg>
);

const CleanupIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M4 7h16M9 7V4h6v3M6 7l1 13a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-13" />
  </svg>
);

export default function Sidebar() {
  const navigate = useNavigate();
  const handleLogout = () => {
    localStorage.removeItem("token");
    navigate("/login");
  };

  const navItems = [
    { path: "/dashboard", label: "Dashboard", icon: <DashboardIcon /> },
    { path: "/servers", label: "Servers", icon: <ServersIcon /> },
    { path: "/projects", label: "Projects", icon: <ProjectsIcon /> },
    { path: "/cleanup", label: "Cleanup", icon: <CleanupIcon /> },
  ];

  return (
    <aside style={{
      width: "240px", minHeight: "100vh", background: "#0f172a",
      display: "flex", flexDirection: "column",
      borderRight: "1px solid #1e293b", flexShrink: 0
    }}>
      <div style={{ padding: "28px 24px 20px", borderBottom: "1px solid #1e293b" }}>
        <div style={{
          width: "40px", height: "40px", borderRadius: "10px",
          background: "linear-gradient(135deg, var(--accent-dim), var(--accent-2))",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: "18px", fontWeight: 800, color: "#fff", marginBottom: "12px",
          animation: "pulse-ring 2.4s ease-out infinite",
        }}>I</div>
        <div style={{ fontSize: "16px", fontWeight: 800, color: "#f1f5f9", letterSpacing: "0.3px" }}>
          Infra Intel
        </div>
        <div style={{ fontSize: "11px", color: "#64748b", letterSpacing: "1.5px", marginTop: "2px" }}>
          AI PLATFORM
        </div>
      </div>

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
            {icon}<span>{label}</span>
          </NavLink>
        ))}
      </div>

      <div style={{ padding: "16px 24px", borderTop: "1px solid #1e293b" }}>
        <button onClick={handleLogout} style={{
          display: "flex", alignItems: "center", gap: "8px",
          background: "none", border: "none", color: "#64748b",
          cursor: "pointer", fontSize: "13px", padding: "0"
        }}>
          <span>↩</span><span>Sign Out</span>
        </button>
        <div style={{ fontSize: "10px", color: "#334155", marginTop: "10px" }}>
          Infra Intel v1.0
        </div>
      </div>
    </aside>
  );
}
