import React, { useState, useEffect } from "react";
import { NavLink } from "react-router-dom";

const navItems = [
  { path: "/dashboard", label: "Dashboard", icon: "📊" },
  { path: "/servers", label: "Servers", icon: "🖥️" },
  { path: "/projects", label: "Projects", icon: "📁" },
  { path: "/duplicates", label: "Duplicates", icon: "👯" },
  { path: "/monitoring", label: "Uptime Monitor", icon: "📡" },
  { path: "/alerts", label: "Alerts", icon: "🔔" },
  { path: "/logs", label: "Log Explorer", icon: "📜" },
  { path: "/api-keys", label: "API Keys AuthGuard", icon: "🔑" },
  { path: "/intelligence", label: "ML & AI Intel", icon: "⚡" },
];

function NavContent({ onClose }) {
  const handleLogout = () => {
    localStorage.removeItem("token");
    window.location.href = "/login";
    if (onClose) onClose();
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", background: "#0d1524", borderRight: "1px solid #1d3047" }}>
      <div style={{ padding: "24px 20px 20px", borderBottom: "1px solid #1d3047" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div style={{ width: "34px", height: "34px", borderRadius: "10px", background: "linear-gradient(135deg,#0EA5E9,#6366F1)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "18px", fontWeight: 800, color: "white" }}>⚡</div>
            <div>
              <div style={{ fontSize: "15px", fontWeight: 800, color: "#f1f5f9", letterSpacing: "0.02em" }}>Infra Intel</div>
              <div style={{ fontSize: "10px", color: "#38bdf8", letterSpacing: "0.14em", fontWeight: 700 }}>ENTERPRISE AI</div>
            </div>
          </div>
          {onClose && (
            <button onClick={onClose} style={{ background: "none", border: "none", color: "#94a3b8", cursor: "pointer", fontSize: "18px" }}>✕</button>
          )}
        </div>
      </div>

      <nav style={{ flex: 1, padding: "16px 0", overflowY: "auto" }}>
        <div style={{ fontSize: "10px", color: "#475569", letterSpacing: "0.12em", fontWeight: 800, padding: "0 20px", marginBottom: "10px" }}>PLATFORM NAVIGATION</div>
        {navItems.map(({ path, label, icon }) => (
          <NavLink key={path} to={path} onClick={onClose} style={({ isActive }) => ({
            display: "flex", alignItems: "center", gap: "12px",
            padding: "11px 20px", textDecoration: "none", marginBottom: "3px",
            color: isActive ? "#38bdf8" : "#94a3b8",
            background: isActive ? "rgba(56,189,248,0.1)" : "transparent",
            borderLeft: isActive ? "3px solid #38bdf8" : "3px solid transparent",
            fontWeight: isActive ? 700 : 500, fontSize: "14px",
            transition: "all 0.15s ease",
          })}>
            <span style={{ fontSize: "16px" }}>{icon}</span>
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      <div style={{ padding: "16px 20px", borderTop: "1px solid #1d3047", background: "#09111d" }}>
        <button onClick={handleLogout} style={{ width: "100%", background: "rgba(248,113,113,0.08)", border: "1px solid rgba(248,113,113,0.25)", color: "#f87171", borderRadius: "8px", padding: "10px 12px", fontSize: "13px", fontWeight: 600, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: "8px" }}>
          <span>⎋</span><span>Sign Out</span>
        </button>
        <div style={{ textAlign: "center", marginTop: "10px", fontSize: "10px", color: "#475569", fontWeight: 600 }}>v3.0.0 · Enterprise Monitoring Platform</div>
      </div>
    </div>
  );
}

export default function Sidebar() {
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768);
  const [drawerOpen, setDrawerOpen] = useState(false);

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth <= 768);
      if (window.innerWidth > 768) setDrawerOpen(false);
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  if (!isMobile) {
    return (
      <aside style={{ width: "240px", minHeight: "100vh", flexShrink: 0, display: "flex", flexDirection: "column" }}>
        <NavContent />
      </aside>
    );
  }

  return (
    <>
      <div style={{ position: "fixed", top: 0, left: 0, right: 0, height: "56px", background: "#0d1524", borderBottom: "1px solid #1d3047", display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 16px", zIndex: 100 }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div style={{ width: "28px", height: "28px", borderRadius: "8px", background: "linear-gradient(135deg,#0EA5E9,#6366F1)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "14px", fontWeight: 800, color: "white" }}>⚡</div>
          <div style={{ fontSize: "14px", fontWeight: 800, color: "#f1f5f9" }}>Infra Intel</div>
        </div>
        <button onClick={() => setDrawerOpen(true)} style={{ background: "none", border: "none", color: "#94a3b8", cursor: "pointer", padding: "8px", fontSize: "22px" }}>☰</button>
      </div>

      {drawerOpen && (
        <div style={{ position: "fixed", inset: 0, zIndex: 200 }}>
          <div onClick={() => setDrawerOpen(false)} style={{ position: "absolute", inset: 0, background: "rgba(0,0,0,0.7)" }} />
          <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: "260px" }}>
            <NavContent onClose={() => setDrawerOpen(false)} />
          </div>
        </div>
      )}
    </>
  );
}
