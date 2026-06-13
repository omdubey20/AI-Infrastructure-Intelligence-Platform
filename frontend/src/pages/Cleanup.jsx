import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/axios";

export default function Cleanup() {
  const navigate = useNavigate();
  const [report, setReport] = useState(null);

  useEffect(() => {
    api.get("/cleanup/report").then(r => setReport(r.data)).catch(() => {});
  }, []);

  const handleAction = async (projectId, action) => {
    await api.post("/cleanup/approve/" + projectId + "?action=" + action);
    api.get("/cleanup/report").then(r => setReport(r.data)).catch(() => {});
  };

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "#0f172a" }}>
      <aside style={{ width: "240px", background: "#1e293b", padding: "24px 16px", borderRight: "1px solid #334155" }}>
        <h2 style={{ color: "white", fontSize: "18px", fontWeight: "bold", marginBottom: "32px" }}>ServerManager Pro</h2>
        {["/", "/servers", "/projects", "/cleanup"].map((path, i) => {
          const labels = ["Dashboard", "Servers", "Projects", "Cleanup"];
          const icons = ["📊", "🖥️", "📁", "🧹"];
          return (
            <div key={path} onClick={() => navigate(path)} style={{ padding: "10px 16px", borderRadius: "8px", color: window.location.pathname === path ? "white" : "#94a3b8", background: window.location.pathname === path ? "#2563eb" : "transparent", cursor: "pointer", marginBottom: "4px", display: "flex", alignItems: "center", gap: "10px" }}>
              <span>{icons[i]}</span><span>{labels[i]}</span>
            </div>
          );
        })}
      </aside>
      <main style={{ flex: 1, padding: "32px" }}>
        <h1 style={{ color: "white", fontSize: "28px", fontWeight: "bold", marginBottom: "24px" }}>Cleanup</h1>
        {report && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: "16px", marginBottom: "32px" }}>
            {[["Total Projects", report.totalprojects, "#3b82f6"],["Delete Candidates", report.deletecandidates, "#ef4444"],["Archive Candidates", report.archivecandidates, "#f59e0b"],["Keep", report.keepcount, "#10b981"]].map(([label, val, color]) => (
              <div key={label} style={{ background: "#1e293b", borderRadius: "12px", padding: "20px", border: "1px solid #334155" }}>
                <p style={{ color: "#94a3b8", fontSize: "12px", marginBottom: "8px" }}>{label}</p>
                <p style={{ color: color, fontSize: "32px", fontWeight: "bold" }}>{val}</p>
              </div>
            ))}
          </div>
        )}
        <div style={{ background: "#1e293b", borderRadius: "12px", border: "1px solid #334155" }}>
          <div style={{ padding: "16px 24px", borderBottom: "1px solid #334155" }}>
            <h3 style={{ color: "white" }}>Projects Requiring Action</h3>
          </div>
          {report?.projects?.map(p => (
            <div key={p.projectid} style={{ padding: "16px 24px", borderBottom: "1px solid #334155", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <p style={{ color: "white", fontWeight: "600" }}>{p.projectname}</p>
                <p style={{ color: "#94a3b8", fontSize: "12px" }}>{p.servername} • {p.recommendedaction}</p>
              </div>
              <div style={{ display: "flex", gap: "8px" }}>
                <button onClick={() => handleAction(p.projectid, "delete")} style={{ background: "#ef444420", color: "#ef4444", border: "none", padding: "6px 12px", borderRadius: "6px", cursor: "pointer", fontSize: "12px" }}>Delete</button>
                <button onClick={() => handleAction(p.projectid, "archive")} style={{ background: "#f59e0b20", color: "#f59e0b", border: "none", padding: "6px 12px", borderRadius: "6px", cursor: "pointer", fontSize: "12px" }}>Archive</button>
                <button onClick={() => handleAction(p.projectid, "keep")} style={{ background: "#10b98120", color: "#10b981", border: "none", padding: "6px 12px", borderRadius: "6px", cursor: "pointer", fontSize: "12px" }}>Keep</button>
              </div>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}