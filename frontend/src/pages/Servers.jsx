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
        <button onClick={handleOpenAdd} className="btn-primary">+ Add Server</button>
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
                      <span className={s.data_source === "ssh" ? "badge badge-green" : "badge badge-blue"}>
                        {s.data_source === "ssh" ? "LIVE SSH" : s.data_source === "whm" ? "WHM API" : s.data_source || "Estimated"}
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
                        <button onClick={(e) => handleScanSingle(s.id, s.name, e)} className="btn-secondary" style={{ padding: "4px 10px", fontSize: "11px" }}>
                          ⚡ Scan
                        </button>
                        <button onClick={(e) => handleOpenEdit(s, e)} className="btn-secondary" style={{ padding: "4px 10px", fontSize: "11px", background: "rgba(139,92,246,0.15)", color: "#c084fc", border: "1px solid rgba(139,92,246,0.3)" }}>
                          ✏️ Credentials
                        </button>
                        <button onClick={(e) => handleDelete(s.id, s.name, e)} className="btn-danger" style={{ padding: "4px 10px", fontSize: "11px" }}>
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
    </div>
  );
}