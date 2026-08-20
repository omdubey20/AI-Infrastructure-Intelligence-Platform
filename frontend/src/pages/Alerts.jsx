import React, { useEffect, useState } from "react";
import api from "../api/axios";

const TYPE_LABELS = {
  site_down: "🔴 Site Down",
  disk_high: "💾 Disk High",
  cpu_high: "🔥 CPU High",
  memory_high: "🧠 Memory High",
  ssl_expiring: "🔒 SSL Expiring",
  malware: "🦠 Malware",
  agent_offline: "📡 Agent Offline",
};

const SEV_STYLE = {
  critical: { bg: "rgba(248,113,113,0.1)", border: "rgba(248,113,113,0.3)", color: "#f87171", label: "CRITICAL" },
  warning: { bg: "rgba(251,191,36,0.1)", border: "rgba(251,191,36,0.3)", color: "#fbbf24", label: "WARNING" },
  info: { bg: "rgba(56,189,248,0.1)", border: "rgba(56,189,248,0.3)", color: "#38bdf8", label: "INFO" },
};

export default function Alerts() {
  const [alerts, setAlerts] = useState([]);
  const [malware, setMalware] = useState([]);
  const [total, setTotal] = useState(0); // eslint-disable-line no-unused-vars
  const [totalOpen, setTotalOpen] = useState(0);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("open");
  const [typeFilter, setTypeFilter] = useState("all");
  const [actionMsg, setActionMsg] = useState(null);
  const [tab, setTab] = useState("alerts"); // alerts | malware | settings
  const [configForm, setConfigForm] = useState({
    teams_webhook_url: "",
    email_to: "",
    smtp_host: "",
    smtp_port: 587,
    smtp_user: "",
    smtp_password: ""
  });
  const [configStatus, setConfigStatus] = useState({ teams_configured: false, email_configured: false });
  const [savingConfig, setSavingConfig] = useState(false);
  const [testingTeams, setTestingTeams] = useState(false);
  const [testingEmail, setTestingEmail] = useState(false);

  const fetchAlerts = async () => {
    try {
      const params = { limit: 100 };
      if (filter === "open") params.resolved = false;
      else if (filter === "resolved") params.resolved = true;
      if (typeFilter !== "all") params.alert_type = typeFilter;

      const res = await api.get("/alerts/", { params });
      setAlerts(res.data?.alerts || []);
      setTotal(res.data?.total || 0);
      setTotalOpen(res.data?.total_open || 0);
    } catch (e) {
      console.error("fetchAlerts error:", e);
    } finally {
      setLoading(false);
    }
  };

  const fetchMalware = async () => {
    try {
      const res = await api.get("/alerts/malware", { params: { resolved: false } });
      setMalware(Array.isArray(res.data) ? res.data : []);
    } catch (e) {
      console.error("fetchMalware error:", e);
    }
  };

  const fetchConfig = async () => {
    try {
      const res = await api.get("/alerts/config");
      setConfigForm({
        teams_webhook_url: res.data.teams_webhook_url || "",
        email_to: res.data.email_to || "",
        smtp_host: res.data.smtp_host || "",
        smtp_port: res.data.smtp_port || 587,
        smtp_user: res.data.smtp_user || "",
        smtp_password: res.data.smtp_password || ""
      });
      setConfigStatus({
        teams_configured: res.data.teams_configured,
        email_configured: res.data.email_configured
      });
    } catch (e) {
      console.error("fetchConfig error:", e);
    }
  };

  const handleSaveConfig = async (e) => {
    e.preventDefault();
    setSavingConfig(true);
    setActionMsg(null);
    try {
      await api.post("/alerts/config", configForm);
      setActionMsg({ ok: true, msg: "Notification settings saved successfully!" });
      fetchConfig();
    } catch (err) {
      setActionMsg({ ok: false, msg: `Save failed: ${err.response?.data?.detail || err.message}` });
    } finally {
      setSavingConfig(false);
    }
  };

  const handleTestTeams = async () => {
    setTestingTeams(true);
    setActionMsg(null);
    try {
      const res = await api.post("/alerts/test-teams");
      setActionMsg({ ok: true, msg: res.data.message });
    } catch (err) {
      setActionMsg({ ok: false, msg: err.response?.data?.detail || "Teams test failed." });
    } finally {
      setTestingTeams(false);
    }
  };

  const handleTestEmail = async () => {
    setTestingEmail(true);
    setActionMsg(null);
    try {
      const res = await api.post("/alerts/test-email");
      setActionMsg({ ok: true, msg: res.data.message });
    } catch (err) {
      setActionMsg({ ok: false, msg: err.response?.data?.detail || "Email test failed." });
    } finally {
      setTestingEmail(false);
    }
  };

  useEffect(() => {
    fetchAlerts();
    fetchMalware();
    fetchConfig();
    const interval = setInterval(() => { fetchAlerts(); fetchMalware(); }, 300000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter, typeFilter]);

  const handleResolve = async (id) => {
    try {
      await api.post(`/alerts/${id}/resolve`);
      setActionMsg({ ok: true, msg: `Alert #${id} resolved.` });
      fetchAlerts();
    } catch (e) {
      setActionMsg({ ok: false, msg: `Failed: ${e.response?.data?.detail || e.message}` });
    }
  };

  const handleResolveMalware = async (id) => {
    try {
      await api.post(`/alerts/malware/${id}/resolve`);
      setActionMsg({ ok: true, msg: `Malware alert #${id} resolved.` });
      fetchMalware();
    } catch (e) {
      setActionMsg({ ok: false, msg: `Failed: ${e.response?.data?.detail || e.message}` });
    }
  };

  return (
    <div style={{ padding: "32px", background: "#080e1a", minHeight: "100vh" }}>
      {/* Header */}
      <div style={{ marginBottom: "28px" }}>
        <p style={{ fontSize: "11px", color: "#38bdf8", fontWeight: 800, letterSpacing: "0.14em", marginBottom: "6px" }}>
          REAL-TIME ALERT CENTER
        </p>
        <h1 style={{ fontSize: "24px", fontWeight: 800, color: "#f1f5f9" }}>Alerts & Security</h1>
        <p style={{ fontSize: "13px", color: "#94a3b8", marginTop: "4px" }}>
          {totalOpen} open alert(s) · Notifications via Microsoft Teams & Email
        </p>
      </div>

      {actionMsg && (
        <div style={{ padding: "12px 16px", borderRadius: "8px", marginBottom: "20px", background: actionMsg.ok ? "rgba(34,197,94,0.12)" : "rgba(248,113,113,0.12)", border: actionMsg.ok ? "1px solid rgba(34,197,94,0.3)" : "1px solid rgba(248,113,113,0.3)", color: actionMsg.ok ? "#4ade80" : "#f87171", fontSize: "13px", fontWeight: 600 }}>
          {actionMsg.msg}
          <button onClick={() => setActionMsg(null)} style={{ float: "right", background: "none", border: "none", color: "inherit", cursor: "pointer", fontWeight: 800 }}>✕</button>
        </div>
      )}

      {/* Tab Switcher */}
      <div style={{ display: "flex", gap: "8px", marginBottom: "20px" }}>
        {["alerts", "malware", "settings"].map(t => (
          <button key={t} onClick={() => setTab(t)} style={{
            padding: "8px 22px", borderRadius: "20px", border: "none", fontWeight: 700, fontSize: "12px",
            cursor: "pointer", textTransform: "capitalize",
            background: tab === t ? "#38bdf8" : "#111c2e",
            color: tab === t ? "#080e1a" : "#94a3b8",
          }}>
            {t === "alerts" ? `🔔 System Alerts (${totalOpen})` : t === "malware" ? `🦠 Malware (${malware.length})` : "⚙️ Webhook & Email Settings"}
          </button>
        ))}
      </div>

      {/* SYSTEM ALERTS TAB */}
      {tab === "alerts" && (
        <>
          {/* Filters */}
          <div style={{ display: "flex", gap: "8px", marginBottom: "20px", flexWrap: "wrap", alignItems: "center" }}>
            {["open", "resolved", "all"].map(f => (
              <button key={f} onClick={() => setFilter(f)} style={{
                padding: "6px 16px", borderRadius: "16px", border: "none", fontWeight: 700, fontSize: "11px",
                cursor: "pointer", textTransform: "capitalize",
                background: filter === f ? "#6366f1" : "#111c2e",
                color: filter === f ? "#fff" : "#94a3b8",
              }}>{f}</button>
            ))}
            <span style={{ color: "#334155", margin: "0 4px" }}>|</span>
            <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)} style={{
              padding: "6px 12px", borderRadius: "16px", background: "#111c2e", border: "1px solid #1d3047",
              color: "#f1f5f9", fontWeight: 700, fontSize: "11px", cursor: "pointer",
            }}>
              <option value="all">All Types</option>
              {Object.keys(TYPE_LABELS).map(t => (
                <option key={t} value={t}>{TYPE_LABELS[t]}</option>
              ))}
            </select>
          </div>

          {/* Alerts List */}
          {loading ? (
            <div style={{ color: "#94a3b8" }}>Loading alerts...</div>
          ) : alerts.length === 0 ? (
            <div className="card" style={{ textAlign: "center", padding: "48px" }}>
              <p style={{ fontSize: "16px", fontWeight: 700, color: "#4ade80" }}>✅ No alerts!</p>
              <p style={{ fontSize: "13px", color: "#64748b", marginTop: "4px" }}>All systems operating normally.</p>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              {alerts.map(a => {
                const sev = SEV_STYLE[a.severity] || SEV_STYLE.info;
                return (
                  <div key={a.id} className="card" style={{
                    borderLeft: `3px solid ${sev.color}`, background: sev.bg, padding: "16px 20px",
                    opacity: a.is_resolved ? 0.5 : 1,
                  }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "12px" }}>
                      <div style={{ flex: 1 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
                          <span style={{ fontSize: "13px" }}>{TYPE_LABELS[a.type] || a.type}</span>
                          <span style={{ background: `${sev.color}22`, color: sev.color, padding: "2px 8px", borderRadius: "8px", fontSize: "10px", fontWeight: 800 }}>
                            {sev.label}
                          </span>
                          {a.is_resolved && (
                            <span style={{ background: "rgba(34,197,94,0.15)", color: "#4ade80", padding: "2px 8px", borderRadius: "8px", fontSize: "10px", fontWeight: 800 }}>
                              RESOLVED
                            </span>
                          )}
                        </div>
                        <p style={{ color: "#f1f5f9", fontSize: "13px", fontWeight: 600, margin: 0 }}>{a.message}</p>
                        <div style={{ marginTop: "6px", fontSize: "11px", color: "#64748b", display: "flex", gap: "16px", flexWrap: "wrap" }}>
                          {a.server_name && <span>Server: <b>{a.server_name}</b></span>}
                          {a.site_domain && <span>Site: <b>{a.site_domain}</b></span>}
                          <span>{new Date(a.created_at).toLocaleString()}</span>
                          {a.teams_sent_at && <span style={{ color: "#6366f1" }}>Teams ✓</span>}
                          {a.email_sent_at && <span style={{ color: "#2dd4bf" }}>Email ✓</span>}
                        </div>
                      </div>
                      {!a.is_resolved && (
                        <button onClick={() => handleResolve(a.id)} style={{
                          background: "rgba(34,197,94,0.12)", border: "1px solid rgba(34,197,94,0.3)",
                          color: "#4ade80", padding: "6px 14px", borderRadius: "8px", fontSize: "11px",
                          fontWeight: 700, cursor: "pointer", whiteSpace: "nowrap",
                        }}>✓ Resolve</button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}

      {/* MALWARE TAB */}
      {tab === "malware" && (
        <>
          {malware.length === 0 ? (
            <div className="card" style={{ textAlign: "center", padding: "48px" }}>
              <p style={{ fontSize: "16px", fontWeight: 700, color: "#4ade80" }}>✅ No malware threats detected</p>
              <p style={{ fontSize: "13px", color: "#64748b", marginTop: "4px" }}>All servers passed security scanning.</p>
            </div>
          ) : (
            <div className="card" style={{ padding: 0, overflow: "hidden" }}>
              <div style={{ padding: "16px 24px", borderBottom: "1px solid #1d3047" }}>
                <h3 style={{ color: "#f1f5f9", fontSize: "14px", fontWeight: 800 }}>🦠 {malware.length} Malware Threat(s) Detected</h3>
              </div>
              <div className="table-responsive">
                <table>
                  <thead>
                    <tr>
                      <th>Server</th>
                      <th>Threat Type</th>
                      <th>File Path</th>
                      <th>Severity</th>
                      <th>Details</th>
                      <th>Detected</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {malware.map(m => (
                      <tr key={m.id}>
                        <td style={{ fontWeight: 700, color: "#f1f5f9" }}>{m.server_name || `Server ${m.server_id}`}</td>
                        <td>
                          <span style={{ background: "rgba(248,113,113,0.12)", color: "#f87171", padding: "2px 8px", borderRadius: "4px", fontSize: "11px", fontWeight: 700 }}>
                            {m.threat_type?.replace("_", " ").toUpperCase()}
                          </span>
                        </td>
                        <td style={{ fontFamily: "monospace", color: "#64748b", fontSize: "12px", maxWidth: "200px", overflow: "hidden", textOverflow: "ellipsis" }}>
                          {m.file_path}
                        </td>
                        <td>
                          <span className={m.severity === "critical" ? "badge badge-red" : "badge badge-amber"}>
                            {m.severity?.toUpperCase()}
                          </span>
                        </td>
                        <td style={{ color: "#94a3b8", fontSize: "12px", maxWidth: "250px" }}>{m.details}</td>
                        <td style={{ color: "#64748b", fontSize: "11px" }}>{m.detected_at ? new Date(m.detected_at).toLocaleString() : "-"}</td>
                        <td>
                          <button onClick={() => handleResolveMalware(m.id)} style={{
                            background: "rgba(34,197,94,0.12)", border: "1px solid rgba(34,197,94,0.3)",
                            color: "#4ade80", padding: "4px 10px", borderRadius: "6px", fontSize: "11px",
                            fontWeight: 700, cursor: "pointer",
                          }}>Resolve</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}

      {/* SETTINGS TAB */}
      {tab === "settings" && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px" }}>
          {/* Webhook Card */}
          <div className="card" style={{ border: "1px solid rgba(56,189,248,0.2)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <h3 style={{ fontSize: "16px", fontWeight: 800, color: "#f1f5f9" }}>
                💬 Microsoft Teams & Slack Webhook
              </h3>
              <span className={configStatus.teams_configured ? "badge badge-green" : "badge badge-amber"}>
                {configStatus.teams_configured ? "🟢 Active" : "🟡 Not Configured"}
              </span>
            </div>
            <p style={{ fontSize: "12px", color: "#94a3b8", marginBottom: "16px" }}>
              Receive instant Adaptive Cards on Microsoft Teams or Slack channels whenever downtime, CPU/RAM/Disk spikes, or malware are detected.
            </p>

            <form onSubmit={handleSaveConfig}>
              <div style={{ marginBottom: "16px" }}>
                <label style={{ fontSize: "11px", color: "#94a3b8", fontWeight: 700, display: "block", marginBottom: "6px" }}>
                  INCOMING WEBHOOK URL
                </label>
                <input
                  type="text"
                  className="input-base"
                  placeholder="https://outlook.office.com/webhook/... or Slack URL"
                  value={configForm.teams_webhook_url}
                  onChange={(e) => setConfigForm({ ...configForm, teams_webhook_url: e.target.value })}
                />
              </div>

              <div style={{ display: "flex", gap: "10px" }}>
                <button type="submit" disabled={savingConfig} className="btn-primary" style={{ fontSize: "12px", padding: "8px 16px" }}>
                  {savingConfig ? "Saving..." : "💾 Save Webhook"}
                </button>
                <button
                  type="button"
                  onClick={handleTestTeams}
                  disabled={testingTeams || !configForm.teams_webhook_url}
                  className="btn-secondary"
                  style={{ fontSize: "12px", padding: "8px 16px", background: "rgba(99,102,241,0.2)", color: "#a5b4fc", border: "1px solid rgba(99,102,241,0.4)" }}
                >
                  {testingTeams ? "Sending..." : "🚀 Test Webhook Alert"}
                </button>
              </div>
            </form>
          </div>

          {/* Email / SMTP Card */}
          <div className="card" style={{ border: "1px solid rgba(56,189,248,0.2)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <h3 style={{ fontSize: "16px", fontWeight: 800, color: "#f1f5f9" }}>
                📧 Email Alert Notifications (SMTP)
              </h3>
              <span className={configStatus.email_configured ? "badge badge-green" : "badge badge-amber"}>
                {configStatus.email_configured ? "🟢 Active" : "🟡 Incomplete"}
              </span>
            </div>
            <p style={{ fontSize: "12px", color: "#94a3b8", marginBottom: "16px" }}>
              Send HTML email alerts to your engineering team for critical infrastructure events.
            </p>

            <form onSubmit={handleSaveConfig}>
              <div style={{ marginBottom: "12px" }}>
                <label style={{ fontSize: "11px", color: "#94a3b8", fontWeight: 700, display: "block", marginBottom: "4px" }}>
                  RECIPIENT EMAIL ADDRESS
                </label>
                <input
                  type="email"
                  className="input-base"
                  placeholder="alerts@company.com"
                  value={configForm.email_to}
                  onChange={(e) => setConfigForm({ ...configForm, email_to: e.target.value })}
                />
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "10px", marginBottom: "12px" }}>
                <div>
                  <label style={{ fontSize: "11px", color: "#94a3b8", fontWeight: 700, display: "block", marginBottom: "4px" }}>
                    SMTP HOST
                  </label>
                  <input
                    type="text"
                    className="input-base"
                    placeholder="smtp.gmail.com or mail.domain.com"
                    value={configForm.smtp_host}
                    onChange={(e) => setConfigForm({ ...configForm, smtp_host: e.target.value })}
                  />
                </div>
                <div>
                  <label style={{ fontSize: "11px", color: "#94a3b8", fontWeight: 700, display: "block", marginBottom: "4px" }}>
                    PORT
                  </label>
                  <input
                    type="number"
                    className="input-base"
                    placeholder="587"
                    value={configForm.smtp_port}
                    onChange={(e) => setConfigForm({ ...configForm, smtp_port: parseInt(e.target.value) || 587 })}
                  />
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", marginBottom: "16px" }}>
                <div>
                  <label style={{ fontSize: "11px", color: "#94a3b8", fontWeight: 700, display: "block", marginBottom: "4px" }}>
                    SMTP USERNAME
                  </label>
                  <input
                    type="text"
                    className="input-base"
                    placeholder="user@example.com"
                    value={configForm.smtp_user}
                    onChange={(e) => setConfigForm({ ...configForm, smtp_user: e.target.value })}
                  />
                </div>
                <div>
                  <label style={{ fontSize: "11px", color: "#94a3b8", fontWeight: 700, display: "block", marginBottom: "4px" }}>
                    SMTP PASSWORD
                  </label>
                  <input
                    type="password"
                    className="input-base"
                    placeholder="••••••••"
                    value={configForm.smtp_password}
                    onChange={(e) => setConfigForm({ ...configForm, smtp_password: e.target.value })}
                  />
                </div>
              </div>

              <div style={{ display: "flex", gap: "10px" }}>
                <button type="submit" disabled={savingConfig} className="btn-primary" style={{ fontSize: "12px", padding: "8px 16px" }}>
                  {savingConfig ? "Saving..." : "💾 Save Email Settings"}
                </button>
                <button
                  type="button"
                  onClick={handleTestEmail}
                  disabled={testingEmail || !configForm.email_to}
                  className="btn-secondary"
                  style={{ fontSize: "12px", padding: "8px 16px", background: "rgba(45,212,191,0.2)", color: "#2dd4bf", border: "1px solid rgba(45,212,191,0.4)" }}
                >
                  {testingEmail ? "Sending..." : "📧 Test Email Alert"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
