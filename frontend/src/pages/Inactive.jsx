import React, { useEffect, useState } from "react";
import api from "../api/axios";

export default function Inactive() {
  const [inactives, setInactives] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionMsg, setActionMsg] = useState(null);

  const fetchInactives = async () => {
    try {
      const res = await api.get("/projects/inactive");
      setInactives(Array.isArray(res.data) ? res.data : []);
    } catch (e) {
      console.error("fetchInactives error:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInactives();
    const interval = setInterval(fetchInactives, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleAction = async (id, action) => {
    try {
      const res = await api.post(`/cleanup/approve/${id}?action=${action}`);
      setActionMsg({ ok: true, msg: res.data?.message || `${action} action completed.` });
      fetchInactives();
    } catch (e) {
      setActionMsg({ ok: false, msg: `Action failed: ${e.response?.data?.detail || e.message}` });
    }
  };

  return (
    <div style={{ padding: "32px", background: "#080e1a", minHeight: "100vh" }}>
      <div style={{ marginBottom: "28px" }}>
        <p style={{ fontSize: "11px", color: "#38bdf8", fontWeight: 700, letterSpacing: "0.12em", marginBottom: "6px" }}>
          AUTOMATED INACTIVITY AUDITOR
        </p>
        <h1 style={{ fontSize: "24px", fontWeight: 800, color: "#f1f5f9" }}>3+ Year Unused Projects</h1>
        <p style={{ fontSize: "13px", color: "#94a3b8", marginTop: "4px" }}>
          Projects unmodified for over 1,095 days with no active web config or DNS traffic
        </p>
      </div>

      {actionMsg && (
        <div style={{ padding: "12px 16px", borderRadius: "8px", marginBottom: "20px", background: actionMsg.ok ? "rgba(34,197,94,0.12)" : "rgba(248,113,113,0.12)", border: actionMsg.ok ? "1px solid rgba(34,197,94,0.3)" : "1px solid rgba(248,113,113,0.3)", color: actionMsg.ok ? "#4ade80" : "#f87171", fontSize: "13px", fontWeight: 600 }}>
          {actionMsg.msg}
          <button onClick={() => setActionMsg(null)} style={{ float: "right", background: "none", border: "none", color: "inherit", cursor: "pointer", fontWeight: 800 }}>✕</button>
        </div>
      )}

      {loading ? (
        <div style={{ color: "#94a3b8" }}>Auditing inactive projects...</div>
      ) : inactives.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: "48px" }}>
          <p style={{ fontSize: "16px", fontWeight: 700, color: "#4ade80" }}>✅ No stale or 3-year inactive projects!</p>
          <p style={{ fontSize: "13px", color: "#64748b", marginTop: "4px" }}>All deployments are actively maintained or accessed.</p>
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <div style={{ padding: "16px 24px", borderBottom: "1px solid #1d3047" }}>
            <h3 style={{ color: "#f1f5f9", fontSize: "14px", fontWeight: 800 }}>{inactives.length} Inactive Project(s) Detected</h3>
          </div>
          <div className="table-responsive">
            <table>
              <thead>
                <tr>
                  <th>Project Name</th>
                  <th>Server</th>
                  <th>Days Inactive</th>
                  <th>Path</th>
                  <th>DNS Status</th>
                  <th>Recommendation</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {inactives.map((p) => (
                  <tr key={p.id}>
                    <td style={{ fontWeight: 700, color: "#f1f5f9" }}>{p.name || p.project_name}</td>
                    <td style={{ color: "#94a3b8" }}>{p.server_name || `Server ${p.server_id}`}</td>
                    <td>
                      <span className="badge badge-amber">
                        {p.days_since_modified || 1120} days ago
                      </span>
                    </td>
                    <td style={{ fontFamily: "monospace", color: "#64748b", fontSize: "12px" }}>{p.project_path || "-"}</td>
                    <td>
                      <span className={p.dns_points_here ? "badge badge-green" : "badge badge-red"}>
                        {p.dns_points_here ? "● Live DNS" : "● Dead DNS"}
                      </span>
                    </td>
                    <td>
                      <span className={p.recommendation === "delete" ? "badge badge-red" : "badge badge-amber"}>
                        {p.recommendation || "Archive"}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: "flex", gap: "6px" }}>
                        <button onClick={() => handleAction(p.id, "archive")} className="btn-secondary" style={{ padding: "4px 10px", fontSize: "12px" }}>
                          Archive
                        </button>
                        <button onClick={() => handleAction(p.id, "delete")} className="btn-danger" style={{ padding: "4px 10px", fontSize: "12px" }}>
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
