import React, { useEffect, useState } from "react";
import api from "../api/axios";

export default function Cleanup() {
  const [report, setReport] = useState(null);
  const [logs, setLogs] = useState([]);
  const [actionMsg, setActionMsg] = useState(null);

  const loadData = async () => {
    try {
      const rRes = await api.get("/cleanup/report");
      setReport(rRes.data);
    } catch (e) {
      console.error("cleanup report error:", e);
    }
    try {
      const lRes = await api.get("/cleanup/logs");
      setLogs(Array.isArray(lRes.data) ? lRes.data : []);
    } catch (e) {
      // logs endpoint might not exist yet
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 8000);
    return () => clearInterval(interval);
  }, []);

  const handleAction = async (projectId, action) => {
    try {
      const res = await api.post(`/cleanup/approve/${projectId}?action=${action}`);
      setActionMsg({ ok: true, msg: res.data?.message || `${action} completed.` });
      loadData();
    } catch (e) {
      setActionMsg({ ok: false, msg: `Action failed: ${e.response?.data?.detail || e.message}` });
    }
  };

  return (
    <div style={{ padding: "32px", background: "#080e1a", minHeight: "100vh" }}>
      <div style={{ marginBottom: "28px" }}>
        <p style={{ fontSize: "11px", color: "#38bdf8", fontWeight: 800, letterSpacing: "0.14em", marginBottom: "6px" }}>
          APPROVAL-BASED CLEANUP QUEUE
        </p>
        <h1 style={{ fontSize: "24px", fontWeight: 800, color: "#f1f5f9" }}>Cleanup Queue</h1>
        <p style={{ fontSize: "13px", color: "#94a3b8", marginTop: "4px" }}>
          Review and approve automated deletion or archiving recommendations with a complete audit trail
        </p>
      </div>

      {actionMsg && (
        <div style={{ padding: "12px 16px", borderRadius: "8px", marginBottom: "20px", background: actionMsg.ok ? "rgba(34,197,94,0.12)" : "rgba(248,113,113,0.12)", border: actionMsg.ok ? "1px solid rgba(34,197,94,0.3)" : "1px solid rgba(248,113,113,0.3)", color: actionMsg.ok ? "#4ade80" : "#f87171", fontSize: "13px", fontWeight: 600 }}>
          {actionMsg.msg}
          <button onClick={() => setActionMsg(null)} style={{ float: "right", background: "none", border: "none", color: "inherit", cursor: "pointer", fontWeight: 800 }}>✕</button>
        </div>
      )}

      {report && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "16px", marginBottom: "28px" }}>
          <div className="card">
            <p style={{ color: "#64748b", fontSize: "11px", fontWeight: 700 }}>TOTAL DISCOVERIES</p>
            <p style={{ color: "#38bdf8", fontSize: "28px", fontWeight: 800 }}>{report.totalprojects}</p>
          </div>
          <div className="card">
            <p style={{ color: "#64748b", fontSize: "11px", fontWeight: 700 }}>DELETE CANDIDATES</p>
            <p style={{ color: "#f87171", fontSize: "28px", fontWeight: 800 }}>{report.deletecandidates}</p>
          </div>
          <div className="card">
            <p style={{ color: "#64748b", fontSize: "11px", fontWeight: 700 }}>ARCHIVE CANDIDATES</p>
            <p style={{ color: "#fbbf24", fontSize: "28px", fontWeight: 800 }}>{report.archivecandidates}</p>
          </div>
          <div className="card">
            <p style={{ color: "#64748b", fontSize: "11px", fontWeight: 700 }}>ACTIVE KEEP</p>
            <p style={{ color: "#4ade80", fontSize: "28px", fontWeight: 800 }}>{report.keepcount}</p>
          </div>
        </div>
      )}

      {/* Queue Table */}
      <div className="card" style={{ padding: 0, marginBottom: "28px", overflow: "hidden" }}>
        <div style={{ padding: "16px 24px", borderBottom: "1px solid #1d3047" }}>
          <h3 style={{ color: "#f1f5f9", fontSize: "14px", fontWeight: 800 }}>Projects Flagged for Action</h3>
        </div>

        {!report?.projects || report.projects.length === 0 ? (
          <div style={{ padding: "40px", textAlign: "center", color: "#64748b" }}>No projects requiring cleanup action.</div>
        ) : (
          <div className="table-responsive">
            <table>
              <thead>
                <tr>
                  <th>Project</th>
                  <th>Server</th>
                  <th>Recommendation</th>
                  <th>Reason</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {report.projects.map((p) => (
                  <tr key={p.projectid}>
                    <td style={{ fontWeight: 700, color: "#f1f5f9" }}>{p.projectname}</td>
                    <td style={{ color: "#94a3b8" }}>{p.servername}</td>
                    <td>
                      <span className={p.recommendedaction === "DELETE" ? "badge badge-red" : p.recommendedaction === "ARCHIVE" ? "badge badge-amber" : "badge badge-green"}>
                        {p.recommendedaction}
                      </span>
                    </td>
                    <td style={{ color: "#94a3b8", fontSize: "12px" }}>{p.reason}</td>
                    <td>
                      <div style={{ display: "flex", gap: "6px" }}>
                        <button onClick={() => handleAction(p.projectid, "delete")} className="btn-danger" style={{ padding: "4px 10px", fontSize: "12px" }}>Delete</button>
                        <button onClick={() => handleAction(p.projectid, "archive")} className="btn-secondary" style={{ padding: "4px 10px", fontSize: "12px" }}>Archive</button>
                        <button onClick={() => handleAction(p.projectid, "keep")} style={{ background: "rgba(34,197,94,0.1)", color: "#4ade80", border: "1px solid rgba(34,197,94,0.3)", padding: "4px 10px", borderRadius: "6px", cursor: "pointer", fontSize: "12px", fontWeight: 700 }}>Keep</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>


      {/* Action History Audit Logs */}
      {logs.length > 0 && (
        <div className="card" style={{ padding: 0 }}>
          <div style={{ padding: "16px 24px", borderBottom: "1px solid #1d3047" }}>
            <h3 style={{ color: "#f1f5f9", fontSize: "14px", fontWeight: 800 }}>Audit Action History</h3>
          </div>
          {logs.map((l, i) => (
            <div key={i} style={{ padding: "12px 24px", borderBottom: "1px solid rgba(29,48,71,0.5)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <span style={{ color: "#f1f5f9", fontWeight: 700 }}>{l.projectname}</span>
                <span style={{ color: "#64748b", fontSize: "12px", marginLeft: "10px" }}>{l.details}</span>
              </div>
              <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
                <span className={l.action === "delete" ? "badge badge-red" : "badge badge-blue"}>
                  {l.action}
                </span>
                <span style={{ fontSize: "11px", color: "#64748b" }}>by {l.performedby}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}