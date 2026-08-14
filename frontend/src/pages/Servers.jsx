import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/axios";

const initialForm = {
  name: "", ip_address: "", environment: "production", status: "active",
  description: "", ssh_username: "root", ssh_password: "", ssh_port: "22",
  whm_host: "", whm_token: "", whm_port: "2087"
};

export default function Servers() {
  const navigate = useNavigate();
  const [servers, setServers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState(null);
  const [form, setForm] = useState(initialForm);
  const [envFilter, setEnvFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [saving, setSaving] = useState(false);
  const [actionMsg, setActionMsg] = useState(null);

  const fetchServers = async () => {
    try {
      const res = await api.get("/servers/");
      setServers(Array.isArray(res.data) ? res.data : []);
    } catch (e) {
      console.error("fetchServers error:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchServers();
    const interval = setInterval(fetchServers, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleOpenAdd = () => {
    setEditId(null);
    setForm(initialForm);
    setShowForm(true);
  };

  const handleOpenEdit = (s, e) => {
    e.stopPropagation();
    setEditId(s.id);
    setForm({
      name: s.name || "",
      ip_address: s.ip_address || "",
      environment: s.environment || "production",
      status: s.status || "active",
      description: s.description || "",
      ssh_username: s.ssh_username || "root",
      ssh_password: "",
      ssh_port: String(s.ssh_port || "22"),
      whm_host: s.whm_host || s.ip_address || "",
      whm_token: "",
      whm_port: String(s.whm_port || "2087")
    });
    setShowForm(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (editId) {
        await api.put(`/servers/${editId}`, form);
        setActionMsg({ ok: true, msg: `Server '${form.name}' updated and scanning...` });
      } else {
        await api.post("/servers/", form);
        setActionMsg({ ok: true, msg: `Server '${form.name}' added and scanning...` });
      }
      fetchServers();
      setShowForm(false);
      setForm(initialForm);
      setEditId(null);
    } catch (err) {
      setActionMsg({ ok: false, msg: err.response?.data?.detail || "Failed to save server." });
    } finally {
      setSaving(false);
    }
  };

  const handleScanSingle = async (id, name, e) => {
    e.stopPropagation();
    setActionMsg({ ok: true, msg: `Scanning ${name}...` });
    try {
      const res = await api.post(`/servers/${id}/scan`);
      setActionMsg({ ok: true, msg: `Scan complete for ${name}: ${res.data.projects_found || 0} project(s) discovered.` });
      fetchServers();
    } catch (err) {
      setActionMsg({ ok: false, msg: `Scan failed for ${name}: ${err.response?.data?.detail || err.message}` });
    }
  };

  const handleDelete = async (id, name, e) => {
    e.stopPropagation();
    if (!window.confirm(`Delete server '${name}' and all its discovered projects?`)) return;
    try {
      await api.delete(`/servers/${id}`);
      setActionMsg({ ok: true, msg: `Server '${name}' deleted successfully.` });
      fetchServers();
    } catch (err) {
      setActionMsg({ ok: false, msg: `Delete failed: ${err.response?.data?.detail || err.message}` });
    }
  };

  const [agentModalServer, setAgentModalServer] = useState(null);
  const [agentTokenInfo, setAgentTokenInfo] = useState(null);
  const [copied, setCopied] = useState(false);

  const handleOpenAgentModal = async (server) => {
    setAgentModalServer(server);
    setCopied(false);
    try {
      const res = await api.get(`/agent/token/${server.id}`);
      setAgentTokenInfo(res.data);
    } catch (e) {
      console.error("Failed to load agent token:", e);
    }
  };

  const handleCopyAgentCommand = () => {
    if (agentTokenInfo?.install_command) {
      navigator.clipboard.writeText(agentTokenInfo.install_command);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    }
  };

  const filteredServers = servers.filter(s => {
    if (envFilter !== "all" && s.environment !== envFilter) return false;
    if (search && !s.name.toLowerCase().includes(search.toLowerCase()) && !s.ip_address.includes(search)) return false;
    return true;
  });

  return (
    <div style={{ padding: "32px", background: "#080e1a", minHeight: "100vh" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "28px", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <p style={{ fontSize: "11px", color: "#38bdf8", fontWeight: 800, letterSpacing: "0.14em", marginBottom: "6px" }}>
            INFRASTRUCTURE FLEET
          </p>
          <h1 style={{ fontSize: "24px", fontWeight: 800, color: "#f1f5f9" }}>Servers</h1>
          <p style={{ fontSize: "13px", color: "#94a3b8", marginTop: "4px" }}>
            {servers.length} server(s) registered across environments
          </p>
        </div>
        <div style={{ display: "flex", gap: "10px" }}>
          {servers.length > 0 && (
            <button
              onClick={() => handleOpenAgentModal(servers[0])}
              style={{
                background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
                color: "white",
                border: "none",
                borderRadius: "10px",
                padding: "10px 18px",
                fontSize: "13px",
                fontWeight: 700,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "8px",
                boxShadow: "0 0 16px rgba(99,102,241,0.3)",
              }}
            >
              <span>⚡</span>
              <span>Install 24/7 Agent</span>
            </button>
          )}
          <button onClick={handleOpenAdd} className="btn-primary">+ Add Server</button>
        </div>
      </div>

      {actionMsg && (
        <div style={{ padding: "12px 16px", borderRadius: "8px", marginBottom: "20px", background: actionMsg.ok ? "rgba(34,197,94,0.12)" : "rgba(248,113,113,0.12)", border: actionMsg.ok ? "1px solid rgba(34,197,94,0.3)" : "1px solid rgba(248,113,113,0.3)", color: actionMsg.ok ? "#4ade80" : "#f87171", fontSize: "13px", fontWeight: 600 }}>
          {actionMsg.msg}
          <button onClick={() => setActionMsg(null)} style={{ float: "right", background: "none", border: "none", color: "inherit", cursor: "pointer", fontWeight: 800 }}>✕</button>
        </div>
      )}

      {/* Filter Tabs & Search */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px", gap: "16px", flexWrap: "wrap" }}>
        <div style={{ display: "flex", gap: "8px" }}>
          {["all", "production", "staging", "development", "testing"].map((env) => (
            <button key={env} onClick={() => setEnvFilter(env)} style={{
              padding: "8px 16px", borderRadius: "20px", border: "none", fontWeight: 700, fontSize: "12px",
              cursor: "pointer", textTransform: "capitalize",
              background: envFilter === env ? "#38bdf8" : "#111c2e",
              color: envFilter === env ? "#080e1a" : "#94a3b8"
            }}>
              {env}
            </button>
          ))}
        </div>
        <input type="text" placeholder="Search by server name or IP..." value={search} onChange={(e) => setSearch(e.target.value)} className="input-base" style={{ width: "280px" }} />
      </div>

      {loading ? (
        <div style={{ color: "#94a3b8" }}>Loading server fleet...</div>
      ) : filteredServers.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: "48px" }}>
          <p style={{ color: "#94a3b8", fontSize: "15px" }}>No servers found.</p>
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <div className="table-responsive">
            <table>
              <thead>
                <tr>
                  <th>Server Name</th>
                  <th>IP Address</th>
                  <th>Environment</th>
                  <th>Source</th>
                  <th>CPU / RAM / Disk</th>
                  <th>Projects</th>
                  <th>Risk</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredServers.map((s) => (
                  <tr key={s.id} onClick={() => navigate(`/servers/${s.id}`)} style={{ cursor: "pointer" }}>
                    <td style={{ fontWeight: 800, color: "#f1f5f9" }}>{s.name}</td>
                    <td style={{ fontFamily: "monospace", color: "#38bdf8" }}>{s.ip_address}</td>
                    <td>
                      <span className={s.environment === "production" ? "badge badge-red" : "badge badge-amber"}>
                        {s.environment}
                      </span>
                    </td>
                    <td>
                      <span className={s.data_source === "agent" ? "badge badge-green" : (s.data_source === "ssh" ? "badge badge-green" : "badge badge-blue")}>
                        {s.data_source === "agent" ? "🎯 24/7 AGENT" : (s.data_source === "ssh" ? "LIVE SSH" : (s.data_source === "whm" ? "WHM API" : s.data_source || "Estimated"))}
                      </span>
                    </td>
                    <td>
                      <span style={{ fontSize: "12px", color: "#94a3b8" }}>
                        {s.cpu_usage || 0}% / {s.memory_usage || 0}% / {s.disk_usage || 0}%
                      </span>
                    </td>
                    <td style={{ fontWeight: 800, color: "#f1f5f9" }}>{s.projects_count ?? 0}</td>
                    <td style={{ fontWeight: 800, color: (s.risk_score || 0) >= 60 ? "#f87171" : "#4ade80" }}>
                      {s.risk_score || 0}
                    </td>
                    <td>
                      <div style={{ display: "flex", gap: "6px" }}>
                        <button onClick={(e) => { e.stopPropagation(); handleOpenAgentModal(s); }} className="btn-secondary" style={{ padding: "4px 8px", fontSize: "11px", background: "rgba(99,102,241,0.15)", color: "#818cf8", border: "1px solid rgba(99,102,241,0.3)", fontWeight: 700 }}>
                          ⚡ 24/7 Agent
                        </button>
                        <button onClick={(e) => handleScanSingle(s.id, s.name, e)} className="btn-secondary" style={{ padding: "4px 8px", fontSize: "11px" }}>
                          🔍 Scan
                        </button>
                        <button onClick={(e) => handleOpenEdit(s, e)} className="btn-secondary" style={{ padding: "4px 8px", fontSize: "11px", background: "rgba(139,92,246,0.15)", color: "#c084fc", border: "1px solid rgba(139,92,246,0.3)" }}>
                          ✏️ Creds
                        </button>
                        <button onClick={(e) => handleDelete(s.id, s.name, e)} className="btn-danger" style={{ padding: "4px 8px", fontSize: "11px" }}>
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

      {/* Add / Edit Server Modal */}
      {showForm && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
          <div className="card" style={{ width: "100%", maxWidth: "500px", background: "#0d1524" }}>
            <h3 style={{ fontSize: "18px", fontWeight: 800, marginBottom: "20px", color: "#f1f5f9" }}>
              {editId ? `Edit Credentials for ${form.name}` : "Add New Infrastructure Server"}
            </h3>
            <form onSubmit={handleSubmit}>
              <div style={{ marginBottom: "14px" }}>
                <label style={{ fontSize: "12px", color: "#94a3b8", fontWeight: 700 }}>SERVER NAME</label>
                <input className="input-base" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="prod-web-01" />
              </div>
              <div style={{ marginBottom: "14px" }}>
                <label style={{ fontSize: "12px", color: "#94a3b8", fontWeight: 700 }}>IP ADDRESS</label>
                <input className="input-base" required value={form.ip_address} onChange={(e) => setForm({ ...form, ip_address: e.target.value })} placeholder="192.168.1.100" />
              </div>
              <div style={{ marginBottom: "14px" }}>
                <label style={{ fontSize: "12px", color: "#94a3b8", fontWeight: 700 }}>SSH USERNAME</label>
                <input className="input-base" value={form.ssh_username} onChange={(e) => setForm({ ...form, ssh_username: e.target.value })} placeholder="root" />
              </div>
              <div style={{ marginBottom: "14px" }}>
                <label style={{ fontSize: "12px", color: "#94a3b8", fontWeight: 700 }}>SSH PASSWORD (encrypted in DB)</label>
                <input className="input-base" type="password" value={form.ssh_password} onChange={(e) => setForm({ ...form, ssh_password: e.target.value })} placeholder="Leave blank to keep existing password" />
              </div>
              <div style={{ marginBottom: "20px" }}>
                <label style={{ fontSize: "12px", color: "#94a3b8", fontWeight: 700 }}>WHM HOST & API TOKEN (optional)</label>
                <input className="input-base" value={form.whm_host} onChange={(e) => setForm({ ...form, whm_host: e.target.value })} placeholder="whm.example.com or IP" style={{ marginBottom: "8px" }} />
                <input className="input-base" type="password" value={form.whm_token} onChange={(e) => setForm({ ...form, whm_token: e.target.value })} placeholder="WHM API Token (leave blank to keep existing)" />
              </div>
              <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end" }}>
                <button type="button" onClick={() => { setShowForm(false); setEditId(null); }} className="btn-secondary">Cancel</button>
                <button type="submit" disabled={saving} className="btn-primary">{saving ? "Saving..." : editId ? "Update & Scan" : "Add Server & Scan"}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 24/7 Agent Install Modal */}
      {agentModalServer && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.8)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: "20px" }}>
          <div style={{ background: "#111c2e", border: "1px solid #2b4565", borderRadius: "16px", padding: "32px", maxWidth: "680px", width: "100%" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <span style={{ fontSize: "24px" }}>⚡</span>
                <h2 style={{ fontSize: "18px", fontWeight: 800, margin: 0, color: "#f1f5f9" }}>
                  Install 24/7 Monitoring Agent (DataDog Style)
                </h2>
              </div>
              <button onClick={() => setAgentModalServer(null)} style={{ background: "none", border: "none", color: "#94a3b8", fontSize: "20px", cursor: "pointer" }}>✕</button>
            </div>

            <p style={{ color: "#94a3b8", fontSize: "13px", lineHeight: "1.5", marginBottom: "16px" }}>
              Run this 1-line command on <strong>{agentModalServer.name}</strong> ({agentModalServer.ip_address}) as <code>root</code> in Terminal / WHM Terminal. It installs a lightweight background daemon (&lt;5MB RAM) that streams live kernel metrics and process hogs directly to your platform.
            </p>

            {/* Server Selector if multiple servers */}
            {servers.length > 1 && (
              <div style={{ marginBottom: "14px" }}>
                <label style={{ fontSize: "12px", color: "#64748b", fontWeight: 700, display: "block", marginBottom: "6px" }}>TARGET SERVER:</label>
                <select
                  value={agentModalServer.id}
                  onChange={(e) => {
                    const s = servers.find(x => x.id === parseInt(e.target.value));
                    if (s) handleOpenAgentModal(s);
                  }}
                  style={{ width: "100%", background: "#0d1524", border: "1px solid #1d3047", borderRadius: "8px", padding: "8px 12px", color: "white", fontSize: "13px" }}
                >
                  {servers.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} ({s.ip_address}) {s.agent_installed ? "— ● 24/7 Agent Active" : ""}
                    </option>
                  ))}
                </select>
              </div>
            )}

            <div style={{ background: "#060b13", border: "1px solid #1d3047", borderRadius: "10px", padding: "16px", marginBottom: "20px", position: "relative" }}>
              <div style={{ fontSize: "11px", color: "#64748b", fontWeight: 700, letterSpacing: "0.08em", marginBottom: "8px" }}>ONE-LINE INSTALL COMMAND</div>
              <pre style={{ margin: 0, color: "#38bdf8", fontFamily: "monospace", fontSize: "13px", whiteSpace: "pre-wrap", wordBreak: "break-all" }}>
                {agentTokenInfo?.install_command || "Generating command..."}
              </pre>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "12px" }}>
              <button
                onClick={handleCopyAgentCommand}
                style={{
                  background: copied ? "linear-gradient(135deg, #059669, #10b981)" : "linear-gradient(135deg, #0284c7, #2563eb)",
                  color: "white",
                  border: "none",
                  borderRadius: "8px",
                  padding: "10px 20px",
                  fontSize: "13px",
                  fontWeight: 700,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px"
                }}
              >
                <span>{copied ? "✓" : "📋"}</span>
                <span>{copied ? "Copied to Clipboard!" : "Copy 1-Line Command"}</span>
              </button>

              <button
                onClick={() => setAgentModalServer(null)}
                style={{ background: "#1e293b", border: "none", color: "#94a3b8", borderRadius: "8px", padding: "10px 18px", fontSize: "13px", cursor: "pointer" }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}