import React, { useEffect, useState } from "react";
import api from "../api/axios";

const FILTERS = ["all", "live"];


export default function Projects() {
  const [projects, setProjects] = useState([]);
  const [servers, setServers] = useState([]);
  const [filter, setFilter] = useState("all");
  const [serverId, setServerId] = useState("all");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [totalCount, setTotalCount] = useState(0);
  const [actionMsg, setActionMsg] = useState(null);

  const fetchServers = async () => {
    try {
      const res = await api.get("/servers/");
      setServers(Array.isArray(res.data) ? res.data : []);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchProjects = async (isInitial = false) => {
    try {
      if (isInitial) setLoading(true);
      const params = { filter, search, limit: 1000 };
      if (serverId !== "all") {
        params.server_id = serverId;
      }
      const res = await api.get("/projects/", { params });
      const data = res.data?.projects || res.data || [];
      setProjects(Array.isArray(data) ? data : []);
      setTotalCount(res.data?.total || data.length);
    } catch (e) {
      console.error("fetchProjects error:", e);
    } finally {
      if (isInitial) setLoading(false);
    }
  };

  useEffect(() => {
    fetchServers();
    fetchProjects(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    fetchProjects(false);
    const interval = setInterval(() => fetchProjects(false), 20000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter, serverId, search]);


  const handleDelete = async (id, name) => {
    if (!window.confirm(`Are you sure you want to remove project "${name}" from discovery?`)) return;
    try {
      await api.delete(`/projects/${id}`);
      setActionMsg({ ok: true, msg: `Project "${name}" removed.` });
      fetchProjects();
    } catch (err) {
      setActionMsg({ ok: false, msg: `Failed to remove: ${err?.response?.data?.detail || err.message}` });
    }
  };

  const riskColor = (score) => {
    if (!score && score !== 0) return "#94a3b8";
    if (score >= 60) return "var(--red)";
    if (score >= 30) return "var(--yellow)";
    return "var(--green)";
  };

  return (
    <div style={{ padding: "32px", maxWidth: "1400px", margin: "0 auto" }}>
      {/* Header */}
      <div style={{ marginBottom: "28px", display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <h1 style={{ fontSize: "24px", fontWeight: 800, color: "#f1f5f9", marginBottom: "6px" }}>
            Live Projects Directory
          </h1>
          <p style={{ color: "#94a3b8", fontSize: "14px" }}>
            All active web applications, PHP frameworks, and domain discoveries across connected servers ({totalCount} live projects)
          </p>
        </div>
      </div>

      {actionMsg && (
        <div style={{ padding: "12px 16px", borderRadius: "8px", marginBottom: "20px", background: actionMsg.ok ? "rgba(34,197,94,0.12)" : "rgba(248,113,113,0.12)", border: actionMsg.ok ? "1px solid rgba(34,197,94,0.3)" : "1px solid rgba(248,113,113,0.3)", color: actionMsg.ok ? "#4ade80" : "#f87171", fontSize: "13px", fontWeight: 600 }}>
          {actionMsg.msg}
          <button onClick={() => setActionMsg(null)} style={{ float: "right", background: "none", border: "none", color: "inherit", cursor: "pointer", fontWeight: 800 }}>✕</button>
        </div>
      )}

      {/* Filter Tabs, Server Select & Search */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px", gap: "16px", flexWrap: "wrap" }}>
        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", alignItems: "center" }}>
          {FILTERS.map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              style={{
                padding: "8px 18px", borderRadius: "20px", border: "none", fontWeight: 700, fontSize: "12px",
                cursor: "pointer", textTransform: "capitalize",
                background: filter === f ? "#38bdf8" : "#111c2e",
                color: filter === f ? "#080e1a" : "#94a3b8"
              }}
            >
              {f === "live" ? "Active Live" : "All Live Projects"}
            </button>
          ))}

          <select
            value={serverId}
            onChange={(e) => setServerId(e.target.value)}
            style={{
              padding: "8px 14px", borderRadius: "20px", background: "#111c2e", border: "1px solid #1d3047",
              color: "#f1f5f9", fontWeight: 700, fontSize: "12px", cursor: "pointer"
            }}
          >
            <option value="all">All Servers ({servers.length})</option>
            {servers.map((s) => (
              <option key={s.id} value={s.id}>
                Server: {s.name} ({s.projects_count || 0} projs)
              </option>
            ))}
          </select>
        </div>

        <input
          type="text"
          placeholder="Search by project, domain, or path..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="input-base"
          style={{ width: "300px" }}
        />
      </div>

      {/* Table */}
      {loading ? (
        <div style={{ color: "#94a3b8" }}>Loading project discovery records...</div>
      ) : projects.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: "48px" }}>
          <p style={{ color: "#94a3b8", fontSize: "15px" }}>No projects match your query.</p>
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <div className="table-responsive">
            <table>
              <thead>
                <tr>
                  <th>Project Name</th>
                  <th>Server</th>
                  <th>Framework</th>
                  <th>Domain</th>
                  <th>Path</th>
                  <th>Status</th>
                  <th>DNS Status</th>
                  <th>Risk</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {projects.map((p) => {
                  return (
                    <tr key={p.id}>
                      <td style={{ fontWeight: 800, color: "#f1f5f9" }}>{p.project_name || p.name}</td>
                      <td style={{ color: "#94a3b8" }}>{p.server_name || `Server ${p.server_id}`}</td>
                      <td>
                        <span style={{ background: "rgba(56,189,248,0.12)", color: "#38bdf8", padding: "2px 8px", borderRadius: "4px", fontSize: "11px", fontWeight: 700, textTransform: "uppercase" }}>
                          {p.framework || "unknown"}
                        </span>
                      </td>
                      <td style={{ fontFamily: "monospace", color: "#38bdf8" }}>{p.domain || "-"}</td>
                      <td style={{ fontFamily: "monospace", color: "#64748b", fontSize: "12px" }}>{p.project_path || "-"}</td>
                      <td>
                        <span className="badge badge-green">
                          ● Active (Live)
                        </span>
                      </td>
                      <td>
                        <span className={p.dns_points_here ? "badge badge-green" : "badge badge-red"}>
                          {p.dns_points_here ? "● Live DNS" : "● Dead DNS"}
                        </span>
                      </td>
                      <td style={{ fontWeight: 800, color: riskColor(p.risk_score) }}>{p.risk_score ?? "-"}</td>
                      <td>
                        <button onClick={() => handleDelete(p.id, p.project_name || p.name)} className="btn-danger" style={{ padding: "4px 10px", fontSize: "11px" }}>
                          Delete
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}