import React, { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";

const DashboardIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
    e x1="5" y1="20" x2="5" y2="13" />e x1="12" y1="20" x2="12" y2="6" />e x1="19" y1="20" x2="19" y2="16" />
  </svg>
);
const ServersIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="3" width="18" height="7" rx="1.5" /><rect x="3" y="14" width="18" height="7" rx="1.5" />
    ircle cx="7" cy="6.5" r="0.8" fill="currentColor" stroke="none" />ircle cx="7" cy="17.5" r="0.8" fill="currentColor" stroke="none" />
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

const navItems = [
  { path: "/dashboard", label: "Dashboard", icon: <DashboardIcon /> },
  { path: "/servers", label: "Servers", icon: <ServersIcon /> },
  { path: "/projects", label: "Projects", icon: <ProjectsIcon /> },
  { path: "/cleanup", label: "Cleanup", icon: <CleanupIcon /> },
];

function SidebarContent({ onClose }) {
  const navigate = useNavigate();
  const handleLogout = () => {
    localStorage.removeItem("token");
    navigate("/login");
    if (onClose) onClose();
  };

  return (
    <div style={{ display:"flex", flexDirection:"column", height:"100%", background:"#0f172a" }}>
      <div style={{ padding:"24px 20px 20px", borderBottom:"1px solid #1e293b" }}>
        <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between" }}>
          <div style={{ display:"flex", alignItems:"center", gap:"10px" }}>
            <div style={{ width:"32px", height:"32px", borderRadius:"8px", background:"linear-gradient(135deg,#0EA5E9,#2DD4BF)", display:"flex", alignItems:"center", justifyContent:"center", fontSize:"16px", fontWeight:800, color:"white" }}>A</div>
            <div>
              <div style={{ fontSize:"14px", fontWeight:800, color:"#f1f5f9" }}>Infra Intel</div>
              <div style={{ fontSize:"10px", color:"#38bdf8", letterSpacing:"0.12em", fontWeight:600 }}>AI PLATFORM</div>
            </div>
          </div>
          {onClose && (
            <button onClick={onClose} style={{ background:"none", border:"none", color:"#64748b", cursor:"pointer", fontSize:"20px", padding:"4px" }}>✕</button>
          )}
        </div>
      </div>

      <nav style={{ flex:1, padding:"12px 0" }}>
        <div style={{ fontSize:"10px", color:"#475569", letterSpacing:"0.1em", fontWeight:700, padding:"0 20px", marginBottom:"8px" }}>NAVIGATION</div>
        {navItems.map(({ path, label, icon }) => (
          <NavLink key={path} to={path} onClick={onClose} style={({ isActive }) => ({
            display:"flex", alignItems:"center", gap:"12px",
            padding:"10px 20px", textDecoration:"none", marginBottom:"2px",
            color: isActive ? "#38bdf8" : "#94a3b8",
            background: isActive ? "rgba(56,189,248,0.08)" : "transparent",
            borderLeft: isActive ? "2px solid #38bdf8" : "2px solid transparent",
            fontWeight: isActive ? 600 : 400, fontSize:"14px",
          })}>
            <span>{icon}</span><span>{label}</span>
          </NavLink>
        ))}
      </nav>

      <div style={{ padding:"16px 20px", borderTop:"1px solid #1e293b" }}>
        <button onClick={handleLogout} style={{ width:"100%", background:"transparent", border:"1px solid #1e293b", color:"#64748b", borderRadius:"8px", padding:"9px 12px", fontSize:"13px", cursor:"pointer", display:"flex", alignItems:"center", gap:"8px" }}>
          <span>⎋</span><span>Sign Out</span>
        </button>
        <div style={{ textAlign:"center", marginTop:"10px", fontSize:"10px", color:"#334155" }}>v1.0.0 · AI-IIP</div>
      </div>
    </div>
  );
}

export default function Sidebar() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <>
      {/* Desktop Sidebar */}
      <aside style={{ width:"240px", minHeight:"100vh", flexShrink:0, display:"flex", flexDirection:"column", borderRight:"1px solid #1e293b" }}
        className="desktop-sidebar">
        <SidebarContent />
      </aside>

      {/* Mobile Top Bar */}
      <div style={{ display:"none" }} className="mobile-topbar">
        <div style={{ position:"fixed", top:0, left:0, right:0, height:"56px", background:"#0f172a", borderBottom:"1px solid #1e293b", display:"flex", alignItems:"center", justifyContent:"space-between", padding:"0 16px", zIndex:100 }}>
          <div style={{ display:"flex", alignItems:"center", gap:"10px" }}>
            <div style={{ width:"28px", height:"28px", borderRadius:"6px", background:"linear-gradient(135deg,#0EA5E9,#2DD4BF)", display:"flex", alignItems:"center", justifyContent:"center", fontSize:"14px", fontWeight:800, color:"white" }}>A</div>
            <div style={{ fontSize:"14px", fontWeight:800, color:"#f1f5f9" }}>Infra Intel</div>
          </div>
          <button onClick={() => setMobileOpen(true)} style={{ background:"none", border:"none", color:"#94a3b8", cursor:"pointer", padding:"8px" }}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              e x1="3" y1="6" x2="21" y2="6"/>e x1="3" y1="12" x2="21" y2="12"/>e x1="3" y1="18" x2="21" y2="18"/>
            </svg>
          </button>
        </div>
      </div>

      {/* Mobile Drawer Overlay */}
      {mobileOpen && (
        <div style={{ position:"fixed", inset:0, zIndex:200 }}>
          <div onClick={() => setMobileOpen(false)} style={{ position:"absolute", inset:0, background:"rgba(0,0,0,0.6)" }} />
          <div style={{ position:"absolute", left:0, top:0, bottom:0, width:"260px", background:"#0f172a", display:"flex", flexDirection:"column" }}>
            <SidebarContent onClose={() => setMobileOpen(false)} />
          </div>
        </div>
      )}

      <style>{`
        @media (max-width: 768px) {
          .desktop-sidebar { display: none !important; }
          .mobile-topbar { display: block !important; }
        }
        @media (min-width: 769px) {
          .mobile-topbar { display: none !important; }
          .desktop-sidebar { display: flex !important; }
        }
      `}</style>
    </>
  );
}
