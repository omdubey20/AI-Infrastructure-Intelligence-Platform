import React, { useEffect, useState } from "react";
import api from "../api/axios";

export default function Duplicates() {
  const [duplicates, setDuplicates] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchDuplicates = async () => {
    try {
      const res = await api.get("/projects/duplicates");
      setDuplicates(Array.isArray(res.data) ? res.data : []);
    } catch (e) {
      console.error("fetchDuplicates error:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDuplicates();
    const interval = setInterval(fetchDuplicates, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleDelete = async (id) => {
    if (!window.confirm("Delete this duplicate project instance?")) return;
    try {
      await api.delete(`/projects/${id}`);
      fetchDuplicates();
    } catch (e) {
      alert(`Failed to delete: ${e.response?.data?.detail || e.message}`);
    }
  };

  return (
    <div style={{ padding: "32px", background: "#080e1a", minHeight: "100vh" }}>
      <div style={{ marginBottom: "28px" }}>
        <p style={{ fontSize: "11px", color: "#38bdf8", fontWeight: 700, letterSpacing: "0.12em", marginBottom: "6px" }}>
          AI DUPLICATE DETECTION ENGINE
        </p>
        <h1 style={{ fontSize: "24px", fontWeight: 800, color: "#f1f5f9" }}>Duplicate Projects</h1>
        <p style={{ fontSize: "13px", color: "#94a3b8", marginTop: "4px" }}>
          Multi-signal duplicate detection combining folder names, git remotes, domains, and fuzzy similarity
        </p>
      </div>

      {loading ? (
        <div style={{ color: "#94a3b8" }}>Scanning for duplicates...</div>
      ) : duplicates.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: "48px" }}>
          <p style={{ fontSize: "16px", fontWeight: 700, color: "#4ade80" }}>✅ No duplicate project deployments found!</p>
          <p style={{ fontSize: "13px", color: "#64748b", marginTop: "4px" }}>All server project instances are unique.</p>
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <div style={{ padding: "16px 24px", borderBottom: "1px solid #1d3047" }}>
            <h3 style={{ color: "#f1f5f9", fontSize: "14px", fontWeight: 800 }}>{duplicates.length} Duplicate(s) Detected</h3>
          </div>
          <div className="table-responsive">
            <table>
              <thead>
                <tr>
                  <th>Project Name</th>
                  <th>Server</th>
                  <th>Domain</th>
                  <th>Path</th>
                  <th>Confidence</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {duplicates.map((p) => (
                  <tr key={p.id}>
                    <td style={{ fontWeight: 700, color: "#f1f5f9" }}>{p.name || p.project_name}</td>
                    <td style={{ color: "#94a3b8" }}>{p.server_name || `Server ${p.server_id}`}</td>
                    <td style={{ fontFamily: "monospace", color: "#38bdf8" }}>{p.domain || "-"}</td>
                    <td style={{ fontFamily: "monospace", color: "#64748b", fontSize: "12px" }}>{p.project_path || "-"}</td>
                    <td>
                      <span className="badge badge-amber">
                        {p.duplicate_confidence || 85}% Match
                      </span>
                    </td>
                    <td>
                      <span className={p.is_live ? "badge badge-green" : "badge badge-red"}>
                        {p.is_live ? "Production Live" : "Duplicate Copy"}
                      </span>
                    </td>
                    <td>
                      {!p.is_live && (
                        <button onClick={() => handleDelete(p.id)} className="btn-danger" style={{ padding: "4px 10px", fontSize: "12px" }}>
                          Delete Copy
                        </button>
                      )}
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
