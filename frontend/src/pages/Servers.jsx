import React, { useEffect, useState } from "react";
import api from "../api/axios";
import { useData } from "../context/DataContext";

const initialForm = { name: "", ip_address: "", environment: "production", status: "active", description: "", ssh_username: "root", ssh_password: "", ssh_port: "22", whm_host: "", whm_token: "", whm_port: "2087" };

export default function Servers() {
  const [servers, setServers] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [editServer, setEditServer] = useState(null);
  const [form, setForm] = useState(initialForm);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);

  const fetchServers = async () => {
    setFetching(true);
    try {
      const res = await api.get("/servers/");
      setServers(Array.isArray(res.data) ? res.data : []);
    } catch (err) {
      setError("Failed to load servers.");
    } finally {
      setFetching(false);
    }
  };

  const { servers: preloaded, loaded } = useData();
  useEffect(() => {
    if (loaded && preloaded && preloaded.length > 0) {
      setServers(preloaded);
      setFetching(false);
    } else {
      fetchServers();
    }
  }, [loaded, preloaded]);

  const openAddForm = () => { setEditServer(null); setForm(initialForm); setError(""); setShowForm(true); };

  const openEditForm = (s) => {
    setEditServer(s);
    setForm({ name: s.name||"", ip_address: s.ip_address||"", environment: s.environment||"production", status: s.status||"active", description: s.description||"", ssh_username: s.ssh_username||"root", ssh_password: "", ssh_port: s.ssh_port||"22", whm_host: s.whm_host||"", whm_token: "", whm_port: s.whm_port||"2087" });
    setError(""); setShowForm(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault(); setLoading(true); setError("");
    try {
      if (editServer) await api.put("/servers/" + editServer.id, form);
      else await api.post("/servers/", form);
      await fetchServers(); setShowForm(false); setEditServer(null); setForm(initialForm);
    } catch (err) { setError(err.response?.data?.detail || "Failed to save."); }
    finally { setLoading(false); }
  };

  const handleDelete = async (id) => {
    const ok = window.confirm("Delete this server?");
    if (!ok) return;
    try { await api.delete("/servers/" + id); await fetchServers(); }
    catch (err) { setError("Failed to delete."); }
  };

  const inp = { width:"100%", padding:"10px 12px", background:"#0f172a", border:"1px solid #334155", borderRadius:"8px", color:"white", fontSize:"14px", boxSizing:"border-box" };
  const lbl = { display:"block", color:"#94a3b8", fontSize:"12px", fontWeight:600, marginBottom:"6px" };

  return (
    <div style={{ padding:"32px", background:"#080e1a", minHeight:"100vh" }}>

      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:"28px" }}>
        <div>
          <p style={{ fontSize:"11px", color:"#38bdf8", fontWeight:700, letterSpacing:"0.12em", marginBottom:"6px" }}>INFRASTRUCTURE</p>
          <h1 style={{ fontSize:"24px", fontWeight:800, color:"#f1f5f9" }}>Servers</h1>
          <p style={{ fontSize:"13px", color:"#94a3b8", marginTop:"4px" }}>{servers.length} server(s) registered</p>
        </div>
        <button onClick={openAddForm} className="btn-primary">+ Add Server</button>
      </div>

      {error && <div style={{ background:"rgba(248,113,113,0.08)", border:"1px solid rgba(248,113,113,0.25)", borderRadius:"8px", padding:"12px 16px", marginBottom:"20px", color:"#f87171", fontSize:"13px" }}>{error}</div>}

      {fetching ? <p style={{ color:"#64748b" }}>Loading...</p> : servers.length === 0 ? (
        <div style={{ textAlign:"center", padding:"60px 0" }}>
          <p style={{ color:"#94a3b8", fontSize:"16px", fontWeight:600 }}>No servers yet</p>
          <p style={{ color:"#64748b", fontSize:"13px", marginTop:"6px" }}>Click + Add Server to get started</p>
        </div>
      ) : (
        <div style={{ display:"flex", flexDirection:"column", gap:"12px" }}>
          {servers.map(server => (
            <div key={server.id} className="card" style={{ padding:"20px 24px", display:"flex", justifyContent:"space-between", alignItems:"center" }}>
              <div>
                <div style={{ fontWeight:700, color:"#f1f5f9", fontSize:"16px", marginBottom:"4px" }}>{server.name}</div>
                <div style={{ fontSize:"13px", color:"#64748b" }}>{server.ip_address} · {server.environment} · {server.status}</div>
                {server.description && <div style={{ fontSize:"12px", color:"#475569", marginTop:"4px" }}>{server.description}</div>}
              </div>
              <div style={{ display:"flex", gap:"8px" }}>
                <button onClick={() => openEditForm(server)} style={{ background:"#334155", color:"#e2e8f0", border:"none", padding:"8px 16px", borderRadius:"8px", fontSize:"13px", cursor:"pointer" }}>Edit</button>
                <button onClick={() => handleDelete(server.id)} style={{ background:"rgba(248,113,113,0.1)", color:"#f87171", border:"1px solid rgba(248,113,113,0.3)", padding:"8px 16px", borderRadius:"8px", fontSize:"13px", cursor:"pointer" }}>Delete</button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showForm && (
        <div style={{ position:"fixed", inset:0, background:"rgba(0,0,0,0.7)", display:"flex", alignItems:"center", justifyContent:"center", zIndex:1000 }}>
          <div style={{ background:"#1e293b", border:"1px solid #334155", borderRadius:"16px", padding:"32px", width:"100%", maxWidth:"480px", maxHeight:"85vh", overflowY:"auto" }}>
            <h2 style={{ color:"#f1f5f9", fontSize:"18px", fontWeight:800, marginBottom:"24px" }}>{editServer ? "Edit Server" : "Add Server"}</h2>
            <form onSubmit={handleSubmit}>
              <div style={{ marginBottom:"16px" }}>
                <label style={lbl}>SERVER NAME</label>
                <input style={inp} value={form.name} onChange={e => setForm({...form, name:e.target.value})} placeholder="Production Server" required />
              </div>
              <div style={{ marginBottom:"16px" }}>
                <label style={lbl}>IP ADDRESS</label>
                <input style={inp} value={form.ip_address} onChange={e => setForm({...form, ip_address:e.target.value})} placeholder="192.168.1.10" required />
              </div>
              <div style={{ marginBottom:"16px" }}>
                <label style={lbl}>DESCRIPTION</label>
                <input style={inp} value={form.description} onChange={e => setForm({...form, description:e.target.value})} placeholder="Main application server" />
              </div>
              <div style={{ marginBottom:"16px" }}>
                
              <div style={{ marginBottom:"16px" }}>
                <label style={lbl}>SSH USERNAME</label>
                <input
                  style={inp}
                  value={form.ssh_username}
                  onChange={e => setForm({ ...form, ssh_username: e.target.value })}
                  placeholder="root"
                />
              </div>

              <div style={{ marginBottom:"16px" }}>
                <label style={lbl}>SSH PASSWORD (optional)</label>
                <input
                  style={inp}
                  type="password"
                  value={form.ssh_password}
                  onChange={e => setForm({ ...form, ssh_password: e.target.value })}
                  placeholder="SSH password"
                />
              </div>

              <div style={{ marginBottom:"16px" }}>
                <label style={lbl}>SSH PORT (optional)</label>
                <input
                  style={inp}
                  value={form.ssh_port}
                  onChange={e => setForm({ ...form, ssh_port: e.target.value })}
                  placeholder="22"
                />
              </div>

              <div style={{ marginBottom:"16px" }}>
                <label style={lbl}>WHM HOST</label>
                <input
                  style={inp}
                  value={form.whm_host}
                  onChange={e => setForm({ ...form, whm_host: e.target.value })}
                  placeholder="013237.vps-10.com"
                />
              </div>

              <div style={{ marginBottom:"16px" }}>
                <label style={lbl}>WHM API TOKEN</label>
                <input
                  style={inp}
                  type="password"
                  value={form.whm_token}
                  onChange={e => setForm({ ...form, whm_token: e.target.value })}
                  placeholder="Paste WHM API token"
                />
              </div>

<label style={lbl}>ENVIRONMENT</label>
                <select style={inp} value={form.environment} onChange={e => setForm({...form, environment:e.target.value})}>
                  <option value="production">Production</option>
                  <option value="staging">Staging</option>
                  <option value="development">Development</option>
                </select>
              </div>
              <div style={{ marginBottom:"24px" }}>
                <label style={lbl}>STATUS</label>
                <select style={inp} value={form.status} onChange={e => setForm({...form, status:e.target.value})}>
                  <option value="active">Active</option>
                  <option value="inactive">Inactive</option>
                  <option value="unreachable">Unreachable</option>
                </select>
              </div>
              <div style={{ display:"flex", gap:"12px", justifyContent:"flex-end" }}>
                <button type="button" onClick={() => setShowForm(false)} style={{ background:"transparent", color:"#94a3b8", border:"1px solid #334155", padding:"10px 20px", borderRadius:"8px", cursor:"pointer" }}>Cancel</button>
                <button type="submit" disabled={loading} style={{ background:"#38bdf8", color:"#0f172a", border:"none", padding:"10px 24px", borderRadius:"8px", fontWeight:700, cursor:"pointer" }}>{loading ? "Saving..." : "Save"}</button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}