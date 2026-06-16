import React, { useEffect, useState } from "react";

import api from "../api/axios";

export default function Cleanup() {
  const [report, setReport] = useState(null);

  useEffect(() => {
    api.get("/cleanup/report").then(r => setReport(r.data)).catch(() => {});
  }, []);

  const handleAction = async (projectId, action) => {
    await api.post("/cleanup/approve/" + projectId + "?action=" + action);
    api.get("/cleanup/report").then(r => setReport(r.data)).catch(() => {});
  };

  return (
    <div style={{ padding: "32px" }}>
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
                <p style={{ color: "#94a3b8", fontSize: "12px" }}>{p.servername} • {p.reason}</p>
                <div style={{ display: "flex", gap: "8px", marginTop: "4px" }}>
                  <span style={{ fontSize: "11px", background: "rgba(56,189,248,0.1)", color: "#38bdf8", padding: "2px 8px", borderRadius: "4px" }}>
                    Risk: {p.riskscore}
                  </span>
                  {p.duplicateconfidence > 0 && (
                    <span style={{ fontSize: "11px", background: "rgba(245,158,11,0.1)", color: "#f59e0b", padding: "2px 8px", borderRadius: "4px" }}>
                      Duplicate: {p.duplicateconfidence}%
                    </span>
                  )}
                  <span style={{ fontSize: "11px", background: p.dns_points_here ? "rgba(34,197,94,0.1)" : "rgba(248,113,113,0.1)", color: p.dns_points_here ? "#22c55e" : "#f87171", padding: "2px 8px", borderRadius: "4px" }}>
                    DNS: {p.dns_points_here ? "Live" : "Dead"}
                  </span>
                </div>
              </div>
              <div style={{ display: "flex", gap: "8px" }}>
                <button onClick={() => handleAction(p.projectid, "delete")} style={{ background: "#ef444420", color: "#ef4444", border: "none", padding: "6px 12px", borderRadius: "6px", cursor: "pointer", fontSize: "12px" }}>Delete</button>
                <button onClick={() => handleAction(p.projectid, "archive")} style={{ background: "#f59e0b20", color: "#f59e0b", border: "none", padding: "6px 12px", borderRadius: "6px", cursor: "pointer", fontSize: "12px" }}>Archive</button>
                <button onClick={() => handleAction(p.projectid, "keep")} style={{ background: "#10b98120", color: "#10b981", border: "none", padding: "6px 12px", borderRadius: "6px", cursor: "pointer", fontSize: "12px" }}>Keep</button>
              </div>
            </div>
          ))}
        </div>
      </div>
  );
}