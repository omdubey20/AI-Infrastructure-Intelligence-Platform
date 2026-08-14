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
  const [agentInfo, setAgentInfo] = useState(null);
  const [showAgentModal, setShowAgentModal] = useState(false);
  const [copied, setCopied] = useState(false);

  const fetchServer = async (isInitial = false) => {
    try {
      if (isInitial) setLoading(true);
      const res = await api.get(`/servers/${id}`);
      setServer(res.data);
    } catch (e) {
      console.error("fetchServer error:", e);
    } finally {
      if (isInitial) setLoading(false);
    }
  };

  const fetchAgentToken = async () => {
    try {
      const res = await api.get(`/agent/token/${id}`);
      setAgentInfo(res.data);
    } catch (e) {
      console.error("fetchAgentToken error:", e);
    }
  };

  useEffect(() => {
    fetchServer(true);
    fetchAgentToken();
    const interval = setInterval(() => fetchServer(false), 20000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const handleCopyCommand = () => {
    if (agentInfo?.install_command) {
      navigator.clipboard.writeText(agentInfo.install_command);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    }
  };

  if (loading) return <div style={{ padding: "32px", color: "#94a3b8" }}>Loading server details...</div>;
  if (!server) return <div style={{ padding: "32px", color: "#f87171" }}>Server not found.</div>;

  let topProcs = [];
  if (server.top_processes) {
    try {
      topProcs = typeof server.top_processes === "string" ? JSON.parse(server.top_processes) : server.top_processes;
    } catch (e) {}
  }

  return (
    <div style={{ padding: "32px", background: "#080e1a", minHeight: "100vh" }}>
      {/* Header */}
      <div style={{ marginBottom: "24px", display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <button onClick={() => navigate("/servers")} style={{ background: "none", border: "none", color: "#38bdf8", cursor: "pointer", fontSize: "13px", fontWeight: 700, marginBottom: "8px" }}>
            ← Back to Servers
          </button>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <h1 style={{ fontSize: "24px", fontWeight: 800, color: "#f1f5f9", margin: 0 }}>{server.name}</h1>
            {server.agent_installed ? (
              <span style={{ background: "rgba(74,222,128,0.12)", color: "#4ade80", border: "1px solid rgba(74,222,128,0.3)", padding: "3px 10px", borderRadius: "12px", fontSize: "11px", fontWeight: 800 }}>
                ● 24/7 AGENT ACTIVE
              </span>
            ) : (
              <span style={{ background: "rgba(148,163,184,0.12)", color: "#94a3b8", border: "1px solid rgba(148,163,184,0.2)", padding: "3px 10px", borderRadius: "12px", fontSize: "11px", fontWeight: 700 }}>
                ○ AGENT NOT INSTALLED
              </span>
            )}
          </div>
          <p style={{ fontSize: "13px", color: "#94a3b8", marginTop: "4px" }}>
            {server.ip_address} · {server.environment} · {server.data_source === "agent" ? "🎯 24/7 DEDICATED AGENT" : (server.data_source === "ssh" ? "LIVE SSH" : "WHM REST API")}
          </p>
        </div>

        <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
          <button
            onClick={() => setShowAgentModal(true)}
            style={{
              background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
              color: "white",
              border: "none",
              borderRadius: "8px",
              padding: "10px 16px",
              fontSize: "13px",
              fontWeight: 700,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "8px",
              boxShadow: "0 0 16px rgba(99,102,241,0.3)"
            }}
          >
            <span>⚡</span>
            <span>Install 24/7 Agent</span>
          </button>
        </div>
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
            Real-Time Kernel Metrics
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
              <p style={{ fontSize: "11px", color: "#64748b", fontWeight: 600 }}>TELEMETRY MODE</p>
              <p style={{ fontSize: "14px", fontWeight: 800, color: server.data_source === "agent" ? "#4ade80" : "#38bdf8" }}>
                {server.data_source === "agent" ? "Agent 24/7" : (server.data_source === "ssh" ? "SSH Polling" : "WHM REST")}
              </p>
            </div>
          </div>
        </div>

        {/* AI & ML Risk Assessment */}
        <div className="card" style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
          <h3 style={{ fontSize: "14px", fontWeight: 800, color: "#94a3b8", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "12px" }}>
            AI Predictive Risk Score
          </h3>
          <RiskGauge score={server.risk_score} />
          <div style={{ textAlign: "center", marginTop: "12px" }}>
            <p style={{ fontSize: "12px", color: "#94a3b8" }}>
              Confidence: <strong style={{ color: "#f1f5f9" }}>{Math.round((server.ai_risk_confidence || 0.85) * 100)}%</strong>
            </p>
            {server.ai_recommendation && (
              <p style={{ fontSize: "12px", color: "#38bdf8", marginTop: "4px" }}>
                {server.ai_recommendation}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Top Kernel Processes (if streamed by agent) */}
      {topProcs.length > 0 && (
        <div className="card" style={{ marginBottom: "24px" }}>
          <h3 style={{ fontSize: "14px", fontWeight: 800, color: "#94a3b8", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "16px" }}>
            ⚡ Top Kernel Processes (Streamed by 24/7 Agent)
          </h3>
          <div className="table-responsive">
            <table>
              <thead>
                <tr>
                  <th>PID</th>
                  <th>User</th>
                  <th>CPU %</th>
                  <th>Memory %</th>
                  <th>Command / Daemon</th>
                </tr>
              </thead>
              <tbody>
                {topProcs.map((proc, idx) => (
                  <tr key={idx}>
                    <td style={{ fontFamily: "monospace", color: "#94a3b8" }}>{proc.pid}</td>
                    <td style={{ color: "#38bdf8", fontWeight: 700 }}>{proc.user}</td>
                    <td style={{ fontWeight: 800, color: proc.cpu > 20 ? "#f87171" : "#4ade80" }}>{proc.cpu}%</td>
                    <td style={{ fontWeight: 800, color: proc.mem > 20 ? "#fbbf24" : "#cbd5e1" }}>{proc.mem}%</td>
                    <td style={{ fontFamily: "monospace", fontSize: "12px", color: "#f1f5f9" }}>{proc.command}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Discovered Web Projects */}
      <div className="card">
        <h3 style={{ fontSize: "14px", fontWeight: 800, color: "#94a3b8", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "16px" }}>
          Discovered Web Projects & Frameworks ({server.projects ? server.projects.length : 0})
        </h3>

        {server.projects?.length === 0 ? (
          <p style={{ color: "#64748b", fontSize: "13px" }}>No projects discovered on this server yet. Projects will be auto-synced within 60 seconds.</p>
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
                  <th>Risk Score</th>
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
                      <span className="badge badge-green">
                        ● Active (Live)
                      </span>
                    </td>
                    <td style={{ fontWeight: 800, color: p.risk_score >= 70 ? "#f87171" : "#4ade80" }}>{p.risk_score}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 24/7 Agent Install Modal */}
      {showAgentModal && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.8)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: "20px" }}>
          <div style={{ background: "#111c2e", border: "1px solid #2b4565", borderRadius: "16px", padding: "32px", maxWidth: "680px", width: "100%" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <span style={{ fontSize: "24px" }}>⚡</span>
                <h2 style={{ fontSize: "18px", fontWeight: 800, margin: 0, color: "#f1f5f9" }}>
                  Install 24/7 Monitoring Agent (DataDog Style)
                </h2>
              </div>
              <button onClick={() => setShowAgentModal(false)} style={{ background: "none", border: "none", color: "#94a3b8", fontSize: "20px", cursor: "pointer" }}>✕</button>
            </div>

            <p style={{ color: "#94a3b8", fontSize: "13px", lineHeight: "1.5", marginBottom: "20px" }}>
              Run this single command on <strong>{server.name}</strong> ({server.ip_address}) as <code>root</code>. It installs a lightweight daemon (&lt;5MB RAM) that streams sub-second CPU spikes, RAM buffers, and process hogs directly to your platform.
            </p>

            <div style={{ background: "#060b13", border: "1px solid #1d3047", borderRadius: "10px", padding: "16px", marginBottom: "20px", position: "relative" }}>
              <div style={{ fontSize: "11px", color: "#64748b", fontWeight: 700, letterSpacing: "0.08em", marginBottom: "8px" }}>ONE-LINE INSTALL COMMAND</div>
              <pre style={{ margin: 0, color: "#38bdf8", fontFamily: "monospace", fontSize: "13px", whiteSpace: "pre-wrap", wordBreak: "break-all" }}>
                {agentInfo?.install_command || "Generating command..."}
              </pre>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "12px" }}>
              <button
                onClick={handleCopyCommand}
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
                onClick={() => setShowAgentModal(false)}
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
