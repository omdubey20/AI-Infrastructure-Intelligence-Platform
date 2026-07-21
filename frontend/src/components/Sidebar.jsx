import React, { useState, useEffect } from "react";
import { NavLink, useNavigate } from "react-router-dom";

const navItems = [
  { path: "/dashboard", label: "Dashboard", icon: "📊" },
  { path: "/servers", label: "Servers", icon: "🖥️" },
  { path: "/projects", label: "Projects", icon: "��" },
  { path: "/cleanup", label: "Cleanup", icon: "🧹" },
];

function NavContent({ onClose }) {
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
            <button onClick={onClose} style={{ background:"none", border:"none", color:"#94a3b8", cursor:"pointer", fontSize:"18px", lineHeight:1 }}>✕</button>
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
            transition:"all 0.15s",
          })}>
            <span style={{ fontSize:"16px" }}>{icon}</span>
            <span>{label}</span>
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
      <aside style={{ width:"240px", minHeight:"100vh", flexShrink:0, display:"flex", flexDirection:"column", borderRight:"1px solid #1e293b" }}>
        <NavContent />
      </aside>
    );
  }

  return (
    <>
      <div style={{ position:"fixed", top:0, left:0, right:0, height:"56px", background:"#0f172a", borderBottom:"1px solid #1e293b", display:"flex", alignItems:"center", justifyContent:"space-between", padding:"0 16px", zIndex:100 }}>
        <div style={{ display:"flex", alignItems:"center", gap:"10px" }}>
          <div style={{ width:"28px", height:"28px", borderRadius:"6px", background:"linear-gradient(135deg,#0EA5E9,#2DD4BF)", display:"flex", alignItems:"center", justifyContent:"center", fontSize:"14px", fontWeight:800, color:"white" }}>A</div>
          <div style={{ fontSize:"14px", fontWeight:800, color:"#f1f5f9" }}>Infra Intel</div>
        </div>
        <button onClick={() => setDrawerOpen(true)} style={{ background:"none", border:"none", color:"#94a3b8", cursor:"pointer", padding:"8px", fontSize:"22px", lineHeight:1 }}>☰</button>
      </div>

      {drawerOpen && (
        <div style={{ position:"fixed", inset:0, zIndex:200 }}>
          <div onClick={() => setDrawerOpen(false)} style={{ position:"absolute", inset:0, background:"rgba(0,0,0,0.6)" }} />
          <div style={{ position:"absolute", left:0, top:0, bottom:0, width:"260px" }}>
            <NavContent onClose={() => setDrawerOpen(false)} />
          </div>
        </div>
      )}
    </>
  );
}
