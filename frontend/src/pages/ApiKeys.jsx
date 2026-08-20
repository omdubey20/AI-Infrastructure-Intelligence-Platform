import React, { useEffect, useState } from "react";
import api from "../api/axios";

export default function ApiKeys() {
  const [keys, setKeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [keyName, setKeyName] = useState("");
  const [keyRole, setKeyRole] = useState("ingest");
  const [creating, setCreating] = useState(false);
  const [createdSecret, setCreatedSecret] = useState(null);
  const [msg, setMsg] = useState(null);

  const fetchKeys = async () => {
    try {
      const res = await api.get("/auth/api-keys/");
      setKeys(Array.isArray(res.data) ? res.data : []);
    } catch (err) {
      console.error("API Keys fetch error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchKeys();
  }, []);

  const handleCreateKey = async (e) => {
    e.preventDefault();
    if (!keyName.trim()) return;
    setCreating(true);
    setMsg(null);
    try {
      const res = await api.post("/auth/api-keys/", { name: keyName.trim(), role: keyRole });
      setCreatedSecret(res.data.api_key);
      setKeyName("");
      fetchKeys();
    } catch (err) {
      setMsg({ ok: false, text: `Creation failed: ${err.response?.data?.detail || err.message}` });
    } finally {
      setCreating(false);
    }
  };

  const handleRevokeKey = async (id, name) => {
    if (!window.confirm(`Are you sure you want to revoke API Key '${name}'?`)) return;
    try {
      await api.delete(`/auth/api-keys/${id}`);
      fetchKeys();
    } catch (err) {
      alert(`Revoke failed: ${err.response?.data?.detail || err.message}`);
    }
  };

  return (
    <div style={{ padding: "24px", color: "#f8fafc" }}>
      <div style={{ marginBottom: "20px" }}>
        <h1 style={{ margin: 0, fontSize: "24px", fontWeight: 700, color: "#f8fafc" }}>
          🔑 API Key Management & AuthGuard
        </h1>
        <p style={{ margin: "4px 0 0", color: "#94a3b8", fontSize: "14px" }}>
          Manage secure API ingestion keys for remote server agents, webhooks, and log ingest nodes.
        </p>
      </div>

      {msg && (
        <div style={{
          padding: "10px 14px", borderRadius: "6px", marginBottom: "16px",
          background: msg.ok ? "rgba(34,197,94,0.15)" : "rgba(239,68,68,0.15)",
          color: msg.ok ? "#4ade80" : "#f87171"
        }}>
          {msg.text}
        </div>
      )}

      {createdSecret && (
        <div style={{
          padding: "16px", borderRadius: "8px", background: "rgba(34,197,94,0.12)",
          border: "1px solid #22c55e", marginBottom: "20px", color: "#f8fafc"
        }}>
          <h4 style={{ margin: "0 0 8px", color: "#4ade80" }}>🎉 API Key Created Successfully!</h4>
          <p style={{ margin: "0 0 8px", fontSize: "13px", color: "#94a3b8" }}>
            Save this key now. It will not be shown again:
          </p>
          <code style={{
            display: "block", padding: "10px", background: "#0f172a", borderRadius: "6px",
            color: "#38bdf8", fontFamily: "monospace", fontSize: "14px", wordBreak: "break-all"
          }}>
            {createdSecret}
          </code>
          <button
            onClick={() => setCreatedSecret(null)}
            style={{ marginTop: "12px", padding: "6px 12px", background: "#334155", color: "#fff", border: "none", borderRadius: "4px", cursor: "pointer" }}
          >
            I have saved this key
          </button>
        </div>
      )}

      {/* Create Form */}
      <div style={{ background: "#1e293b", padding: "20px", borderRadius: "10px", border: "1px solid #334155", marginBottom: "24px" }}>
        <h3 style={{ margin: "0 0 14px", fontSize: "16px" }}>Generate New API Key</h3>
        <form onSubmit={handleCreateKey} style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
          <input
            type="text"
            placeholder="Key Name (e.g. Production Agent Node 01)"
            value={keyName}
            onChange={(e) => setKeyName(e.target.value)}
            style={{ flex: 1, minWidth: "220px", padding: "8px 12px", background: "#0f172a", border: "1px solid #334155", color: "#fff", borderRadius: "6px" }}
            required
          />
          <select
            value={keyRole}
            onChange={(e) => setKeyRole(e.target.value)}
            style={{ padding: "8px 12px", background: "#0f172a", border: "1px solid #334155", color: "#fff", borderRadius: "6px" }}
          >
            <option value="ingest">Ingest (Log & Telemetry POST)</option>
            <option value="read">Read-Only</option>
            <option value="admin">Full Admin Access</option>
          </select>
          <button
            type="submit"
            disabled={creating}
            style={{ padding: "8px 18px", background: "#3b82f6", color: "#fff", border: "none", borderRadius: "6px", fontWeight: 600, cursor: "pointer" }}
          >
            {creating ? "Generating..." : "🔑 Generate Key"}
          </button>
        </form>
      </div>

      {/* Key Table */}
      <div style={{ background: "#1e293b", borderRadius: "10px", border: "1px solid #334155", overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: "13px" }}>
          <thead>
            <tr style={{ background: "#0f172a", color: "#94a3b8", borderBottom: "1px solid #334155" }}>
              <th style={{ padding: "12px 16px" }}>Key Name</th>
              <th style={{ padding: "12px 16px" }}>Key Preview</th>
              <th style={{ padding: "12px 16px" }}>Role Scope</th>
              <th style={{ padding: "12px 16px" }}>Created At</th>
              <th style={{ padding: "12px 16px" }}>Last Used</th>
              <th style={{ padding: "12px 16px", textAlign: "right" }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan="6" style={{ padding: "20px", textAlign: "center", color: "#94a3b8" }}>Loading API Keys...</td></tr>
            ) : keys.length === 0 ? (
              <tr><td colSpan="6" style={{ padding: "20px", textAlign: "center", color: "#64748b" }}>No API Keys configured.</td></tr>
            ) : (
              keys.map((k) => (
                <tr key={k.id} style={{ borderBottom: "1px solid #334155" }}>
                  <td style={{ padding: "12px 16px", fontWeight: 600, color: "#f8fafc" }}>{k.name}</td>
                  <td style={{ padding: "12px 16px", fontFamily: "monospace", color: "#38bdf8" }}>{k.key_preview}</td>
                  <td style={{ padding: "12px 16px" }}>
                    <span style={{ padding: "3px 8px", borderRadius: "4px", background: "rgba(168,85,247,0.15)", color: "#c084fc", fontSize: "11px", fontWeight: 600 }}>
                      {k.role}
                    </span>
                  </td>
                  <td style={{ padding: "12px 16px", color: "#94a3b8" }}>{k.created_at ? new Date(k.created_at).toLocaleDateString() : "N/A"}</td>
                  <td style={{ padding: "12px 16px", color: "#94a3b8" }}>{k.last_used_at ? new Date(k.last_used_at).toLocaleString() : "Never"}</td>
                  <td style={{ padding: "12px 16px", textAlign: "right" }}>
                    <button
                      onClick={() => handleRevokeKey(k.id, k.name)}
                      style={{ padding: "4px 10px", background: "rgba(239,68,68,0.15)", color: "#ef4444", border: "1px solid #ef4444", borderRadius: "4px", cursor: "pointer", fontSize: "12px" }}
                    >
                      Revoke
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
