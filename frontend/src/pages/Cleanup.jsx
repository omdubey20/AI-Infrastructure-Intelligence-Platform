import React, { useEffect, useState } from "react";

import api from "../api/axios";

export default function Cleanup() {
  const [report, setReport] = useState(null);
  const [logs, setLogs] = useState([]);

  const loadData = () => {
    api.get("/cleanup/report").then(r => setReport(r.data)).catch(() => {});
    api.get("/cleanup/logs").then(r => setLogs(Array.isArray(r.data) ? r.data : [])).catch(() => {});
  };

  useEffect(() => { loadData(); }, []);

  const handleAction = async (projectId, action) => {
    await api.post("/cleanup/approve/" + projectId + "?action=" + action);
    loadData();
  };

  return (
    <div style={{ padding: window.innerWidth <= 768 ? "16px" : "32px", background: "#080e1a", minHeight: "100vh" }}>
      <div style={{ marginBottom: "28px" }}>
        <p style={{ fontSize: "11px", color: "#38bdf8", fontWeight: 700, letterSpacing: "0.12em", marginBottom: "6px" }}>INFRASTRUCTURE</p>
        <h1 style={{ fontSize: "24px", fontWeight: 800, color: "#f1f5f9" }}>Cleanup</h1>
        <p style={{ fontSize: "13px", color: "#94a3b8", marginTop: "4px" }}>Review and action projects flagged for cleanup</p>
      </div>

      {report && (
        <div style={{ display: "grid", gridTemplateColumns: window.innerWidth <= 768 ? "repeat(2, 1fr)" : "repeat(4, 1fr)", gap: "16px", marginBottom: "32px" }}>
          {[
            ["Total Projects", report.totalprojects, "#3b82f6"],
            ["Delete Candidates", report.deletecandidates, "#ef4444"],
            ["Archive Candidates", report.archivecandidates, "#f59e0b"],
            ["Keep", report.keepcount, "#10b981"]
          ].map(([label, val, color]) => (
            <div key={label} className="card" style={{ padding: "20px" }}>
              <p style={{ color: "#94a3b8", fontSize: "12px", marginBottom: "8px" }}>{label}</p>
              <p style={{ color: color, fontSize: "32px", fontWeight: 800 }}>{val}</p>
            </div>
          ))}
        </div>
      )}

      <div className="card" style={{ marginBottom: "24px", padding: 0 }}>
        <div style={{ padding: "16px 24px", borderBottom: "1px solid #334155" }}>
          <h3 style={{ color: "#f1f5f9", fontSize: "16px", fontWeight: 700 }}>Projects Requiring Action</h3>
        </div>
        {report?.projects?.length === 0 && (
          <div style={{ padding: "40px", textAlign: "center", color: "#64748b" }}>No projects requiring action</div>
        )}
        {report?.projects?.map(p => (
          <div key={p.projectid} style={{ padding: "16px", borderBottom: "1px solid #334155", display: "flex", flexDirection: window.innerWidth <= 768 ? "column" : "row", justifyContent: "space-between", alignItems: window.innerWidth <= 768 ? "flex-start" : "center", gap: "12px" }}>
            <div>
              <p style={{ color: "#f1f5f9", fontWeight: 600, marginBottom: "4px" }}>{p.projectname}</p>
              <p style={{ color: "#94a3b8", fontSize: "12px" }}>{p.servername} • {p.reason}</p>
              <div style={{ display: "flex", gap: "8px", marginTop: "6px" }}>
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
              <button onClick={() => handleAction(p.projectid, "delete")} style={{ background: "rgba(239,68,68,0.1)", color: "#ef4444", border: "1px solid rgba(239,68,68,0.3)", padding: "6px 14px", borderRadius: "6px", cursor: "pointer", fontSize: "12px", fontWeight: 600 }}>Delete</button>
              <button onClick={() => handleAction(p.projectid, "archive")} style={{ background: "rgba(245,158,11,0.1)", color: "#f59e0b", border: "1px solid rgba(245,158,11,0.3)", padding: "6px 14px", borderRadius: "6px", cursor: "pointer", fontSize: "12px", fontWeight: 600 }}>Archive</button>
              <button onClick={() => handleAction(p.projectid, "keep")} style={{ background: "rgba(16,185,129,0.1)", color: "#10b981", border: "1px solid rgba(16,185,129,0.3)", padding: "6px 14px", borderRadius: "6px", cursor: "pointer", fontSize: "12px", fontWeight: 600 }}>Keep</button>
            </div>
          </div>
        ))}
      </div>

      {logs.length > 0 && (
        <div className="card" style={{ padding: 0 }}>
          <div style={{ padding: "16px 24px", borderBottom: "1px solid #334155" }}>
            <h3 style={{ color: "#f1f5f9", fontSize: "16px", fontWeight: 700 }}>Action History</h3>
          </div>
          {logs.map((log, i) => (
            <div key={i} style={{ padding: "12px 24px", borderBottom: "1px solid #1e293b", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <span style={{ color: "#f1f5f9", fontWeight: 600 }}>{log.projectname}</span>
                <span style={{ color: "#64748b", fontSize: "12px", marginLeft: "8px" }}>{log.servername}</span>
              </div>
              <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
                <span style={{ fontSize: "12px", color: log.action === "deleted" ? "#f87171" : log.action === "archived" ? "#f59e0b" : "#22c55e", fontWeight: 600, textTransform: "uppercase" }}>
                  {log.action}
                </span>
                <span style={{ fontSize: "11px", color: "#475569" }}>by {log.performedby}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}