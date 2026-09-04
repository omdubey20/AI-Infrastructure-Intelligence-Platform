import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from "../api/axios";
import MetricBar from "../components/MetricBar";
import RiskGauge from "../components/RiskGauge";

export default function ServerDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [server, setServer] = useState(null);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [actionMsg, setActionMsg] = useState(null);
  const [agentSetupData, setAgentSetupData] = useState(null);
  const [copied, setCopied] = useState(false);

  const fetchServer = async () => {
    try {
      const res = await api.get(`/servers/${id}`);
      setServer(res.data);
    } catch (e) {
      console.error("fetchServer error:", e);
    } finally {
      setLoading(false);
    }
  };

  const fetchAgentSetup = async () => {
    try {
      const res = await api.get(`/agent/setup-command/${id}`);
      setAgentSetupData(res.data);
    } catch (e) {
      console.error("fetchAgentSetup error:", e);
    }
  };

  useEffect(() => {
    fetchServer();
    fetchAgentSetup();
    const interval = setInterval(() => {
      fetchServer();
      fetchAgentSetup();
    }, 5000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);


  const handleScan = async () => {
    setScanning(true);
    setActionMsg(null);
    try {
      await api.post(`/servers/${id}/scan`);
      setActionMsg({ ok: true, msg: `Discovery scan completed for ${server?.name}` });
      fetchServer();
    } catch (e) {
      setActionMsg({ ok: false, msg: `Scan failed: ${e.response?.data?.detail || e.message}` });
    } finally {
      setScanning(false);
    }
  };

  if (loading) return <div style={{ padding: "32px", color: "#94a3b8" }}>Loading server details...</div>;
  if (!server) return <div style={{ padding: "32px", color: "#f87171" }}>Server not found.</div>;

  return (
    <div style={{ padding: "32px", background: "#080e1a", minHeight: "100vh" }}>
      {/* Header */}
      <div style={{ marginBottom: "24px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <button onClick={() => navigate("/servers")} style={{ background: "none", border: "none", color: "#38bdf8", cursor: "pointer", fontSize: "13px", fontWeight: 700, marginBottom: "8px" }}>
            ← Back to Servers
          </button>
          <h1 style={{ fontSize: "24px", fontWeight: 800, color: "#f1f5f9" }}>{server.name}</h1>
          <p style={{ fontSize: "13px", color: "#94a3b8", marginTop: "4px" }}>
            {server.ip_address} · {server.environment} · {server.data_source === "ssh" ? "LIVE SSH" : "WHM ESTIMATED"}
          </p>
        </div>

        <button onClick={handleScan} disabled={scanning} className="btn-primary">
          {scanning ? <><span className="spinner" /> Scanning...</> : "⚡ Scan Server Now"}
        </button>
      </div>

      {actionMsg && (
        <div style={{ padding: "12px 16px", borderRadius: "8px", marginBottom: "20px", background: actionMsg.ok ? "rgba(34,197,94,0.12)" : "rgba(248,113,113,0.12)", border: actionMsg.ok ? "1px solid rgba(34,197,94,0.3)" : "1px solid rgba(248,113,113,0.3)", color: actionMsg.ok ? "#4ade80" : "#f87171", fontSize: "13px", fontWeight: 600 }}>
          {actionMsg.msg}
          <button onClick={() => setActionMsg(null)} style={{ float: "right", background: "none", border: "none", color: "inherit", cursor: "pointer", fontWeight: 800 }}>✕</button>
        </div>
      )}

      {/* Grid Overview */}
      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "20px", marginBottom: "24px" }}>
        {/* Resource Usage & Metrics */}
        <div className="card">
          <h3 style={{ fontSize: "14px", fontWeight: 800, color: "#94a3b8", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "16px" }}>
            Real-Time Resource Metrics
          </h3>

          <MetricBar label="CPU Usage" value={server.cpu_usage} />
          <MetricBar label="Memory Usage" value={server.memory_usage} />
          <MetricBar label="Disk Usage" value={server.disk_usage} />

          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "12px", marginTop: "20px", background: "#09111d", padding: "16px", borderRadius: "10px" }}>
            <div>
              <p style={{ fontSize: "11px", color: "#64748b", fontWeight: 600 }}>LOAD AVG (1M)</p>
              <p style={{ fontSize: "16px", fontWeight: 800, color: "#f1f5f9" }}>{server.load_avg_1 ?? "-"}</p>
            </div>
            <div>
              <p style={{ fontSize: "11px", color: "#64748b", fontWeight: 600 }}>RAM TOTAL</p>
              <p style={{ fontSize: "16px", fontWeight: 800, color: "#f1f5f9" }}>{server.ram_total_gb ? `${server.ram_total_gb} GB` : "-"}</p>
            </div>
            <div>
              <p style={{ fontSize: "11px", color: "#64748b", fontWeight: 600 }}>UPTIME</p>
              <p style={{ fontSize: "16px", fontWeight: 800, color: "#f1f5f9" }}>{server.uptime_days} days</p>
            </div>
            <div>
              <p style={{ fontSize: "11px", color: "#64748b", fontWeight: 600 }}>ERRORS</p>
              <p style={{ fontSize: "16px", fontWeight: 800, color: server.error_count > 0 ? "#f87171" : "#4ade80" }}>{server.error_count}</p>
            </div>
          </div>
        </div>

        {/* Risk & System Info */}
        <div className="card" style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", textAlign: "center" }}>
          <RiskGauge score={server.risk_score} size={84} />
          <div style={{ marginTop: "16px", fontSize: "13px", color: "#94a3b8" }}>
            <p><strong>OS:</strong> {server.os_name || "Linux"}</p>
            <p><strong>Kernel:</strong> {server.kernel || "-"}</p>
            <p><strong>Architecture:</strong> {server.architecture || "x86_64"}</p>
            <p><strong>Web Server:</strong> {server.web_server || "Nginx/Apache"}</p>
          </div>
        </div>
      </div>

      {/* Agent Setup Card */}
      {agentSetupData && (
        <div className="card" style={{ marginBottom: "24px", border: "1px solid rgba(56,189,248,0.25)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px", flexWrap: "wrap", gap: "12px" }}>
            <div>
              <p style={{ fontSize: "11px", color: "#38bdf8", fontWeight: 800, letterSpacing: "0.12em" }}>AGENT CONNECTION POINT</p>
              <h3 style={{ fontSize: "16px", fontWeight: 800, color: "#f1f5f9", marginTop: "2px" }}>
                1-Line Terminal Install Command for Real-Time Telemetry & Alerts
              </h3>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
              <span className={agentSetupData.agent_installed ? "badge badge-green" : "badge badge-amber"}>
                {agentSetupData.agent_installed ? "🟢 Agent Active" : "🟡 Agent Not Connected"}
              </span>
              {agentSetupData.agent_last_seen && (
                <span style={{ fontSize: "11px", color: "#64748b" }}>
                  Last Heartbeat: {new Date(agentSetupData.agent_last_seen).toLocaleTimeString()}
                </span>
              )}
              <button
                onClick={() => {
                  navigator.clipboard.writeText(agentSetupData.install_command);
                  setCopied(true);
                  setTimeout(() => setCopied(false), 2500);
                }}
                className="btn-primary"
                style={{ fontSize: "12px", padding: "6px 14px" }}
              >
                {copied ? "✓ Copied Command!" : "📋 Copy Terminal Install Command"}
              </button>
            </div>
          </div>

          <pre style={{ margin: 0, fontSize: "12px", background: "#040914", padding: "14px", borderRadius: "8px", color: "#38bdf8", wordBreak: "break-all", whiteSpace: "pre-wrap", fontFamily: "monospace", border: "1px solid #1e293b" }}>
            {agentSetupData.install_command}
          </pre>
          <p style={{ fontSize: "12px", color: "#64748b", marginTop: "10px" }}>
            💡 SSH into <code>{server.ip_address}</code> or open cPanel Terminal / WHM as root and run the command above to start real-time telemetry streaming.
          </p>
        </div>
      )}

      {/* Hosted Projects Table */}
      <div className="card">
        <h3 style={{ fontSize: "14px", fontWeight: 800, color: "#94a3b8", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "16px" }}>
          Hosted Projects ({server.projects_count})
        </h3>

        {server.projects?.length === 0 ? (
          <p style={{ color: "#64748b", fontSize: "13px" }}>No projects discovered on this server yet.</p>
        ) : (
          <div className="table-responsive">
            <table>
              <thead>
                <tr>
                  <th>Project Name</th>
                  <th>Domain</th>
                  <th>Framework</th>
                  <th>Path</th>
                  <th>Status</th>
                  <th>Risk</th>
                </tr>
              </thead>
              <tbody>
                {server.projects.map((p) => (
                  <tr key={p.id}>
                    <td style={{ fontWeight: 700, color: "#f1f5f9" }}>{p.name}</td>
                    <td style={{ fontFamily: "monospace", color: "#38bdf8" }}>{p.domain || "-"}</td>
                    <td>
                      <span style={{ background: "rgba(56,189,248,0.12)", color: "#38bdf8", padding: "2px 8px", borderRadius: "4px", fontSize: "11px", fontWeight: 700 }}>
                        {p.framework || "unknown"}
                      </span>
                    </td>
                    <td style={{ fontFamily: "monospace", color: "#64748b", fontSize: "12px" }}>{p.path}</td>
                    <td>
                      <span className="badge badge-green">● Active</span>
                    </td>

                    <td style={{ fontWeight: 800, color: p.risk_score >= 70 ? "#f87171" : "#4ade80" }}>{p.risk_score}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

      </div>
    </div>
  );
}
