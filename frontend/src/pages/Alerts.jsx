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
    whatsapp_enabled: true,
    whatsapp_user_phone: "",
    whatsapp_group_id: "",
    whatsapp_provider: "callmebot",
    whatsapp_api_key: "",
    whatsapp_gateway_url: "",
    whatsapp_account_sid: "",
    whatsapp_from_phone: "",
    teams_webhook_url: "",
    email_to: "",
    smtp_host: "",
    smtp_port: 587,
    smtp_user: "",
    smtp_password: ""
  });
  const [configStatus, setConfigStatus] = useState({
    whatsapp_configured: false,
    whatsapp_user_configured: false,
    whatsapp_group_configured: false,
    teams_configured: false,
    email_configured: false
  });
  const [savingConfig, setSavingConfig] = useState(false);
  const [testingWaUser, setTestingWaUser] = useState(false);
  const [testingWaGroup, setTestingWaGroup] = useState(false);
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
        whatsapp_enabled: res.data.whatsapp_enabled ?? true,
        whatsapp_user_phone: res.data.whatsapp_user_phone || "",
        whatsapp_group_id: res.data.whatsapp_group_id || "",
        whatsapp_provider: res.data.whatsapp_provider || "callmebot",
        whatsapp_api_key: res.data.whatsapp_api_key || "",
        whatsapp_gateway_url: res.data.whatsapp_gateway_url || "",
        whatsapp_account_sid: res.data.whatsapp_account_sid || "",
        whatsapp_from_phone: res.data.whatsapp_from_phone || "",
        teams_webhook_url: res.data.teams_webhook_url || "",
        email_to: res.data.email_to || "",
        smtp_host: res.data.smtp_host || "",
        smtp_port: res.data.smtp_port || 587,
        smtp_user: res.data.smtp_user || "",
        smtp_password: res.data.smtp_password || ""
      });
      setConfigStatus({
        whatsapp_configured: res.data.whatsapp_configured,
        whatsapp_user_configured: res.data.whatsapp_user_configured,
        whatsapp_group_configured: res.data.whatsapp_group_configured,
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

  const handleTestWaUser = async () => {
    setTestingWaUser(true);
    setActionMsg(null);
    try {
      const res = await api.post("/alerts/test-whatsapp-user");
      setActionMsg({ ok: true, msg: res.data.message });
      if (res.data.preview_url) {
        window.open(res.data.preview_url, "_blank");
      }
    } catch (err) {
      setActionMsg({ ok: false, msg: err.response?.data?.detail || "WhatsApp User test failed." });
    } finally {
      setTestingWaUser(false);
    }
  };

  const handleTestWaGroup = async () => {
    setTestingWaGroup(true);
    setActionMsg(null);
    try {
      const res = await api.post("/alerts/test-whatsapp-group");
      setActionMsg({ ok: true, msg: res.data.message });
    } catch (err) {
      setActionMsg({ ok: false, msg: err.response?.data?.detail || "WhatsApp Group test failed." });
    } finally {
      setTestingWaGroup(false);
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
          {totalOpen} open alert(s) · Notifications via WhatsApp (User & Group) & Email
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
            {t === "alerts" ? `🔔 System Alerts (${totalOpen})` : t === "malware" ? `🦠 Malware (${malware.length})` : "⚙️ WhatsApp & Email Settings"}
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
                const waMessage = `🚨 *INFRASTRUCTURE ALERT: ${(a.type || "ALERT").toUpperCase()}*\n• Server: ${a.server_name || "Unknown"}\n• Severity: ${(a.severity || "warning").toUpperCase()}\n• Message: ${a.message}\n• Timestamp: ${new Date(a.created_at).toLocaleString()}\n• Platform: AI Infrastructure Intelligence`;
                return (
                  <div key={a.id} className="card" style={{
                    borderLeft: `3px solid ${sev.color}`, background: sev.bg, padding: "16px 20px",
                    opacity: a.is_resolved ? 0.5 : 1,
                  }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "12px", flexWrap: "wrap" }}>
                      <div style={{ flex: 1, minWidth: "260px" }}>
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
                        <div style={{ marginTop: "6px", fontSize: "11px", color: "#64748b", display: "flex", gap: "16px", flexWrap: "wrap", alignItems: "center" }}>
                          {a.server_name && <span>Server: <b>{a.server_name}</b></span>}
                          {a.site_domain && <span>Site: <b>{a.site_domain}</b></span>}
                          <span>{new Date(a.created_at).toLocaleString()}</span>
                          {a.whatsapp_sent_at && <span style={{ color: "#22c55e", fontWeight: 700 }}>WhatsApp ✓</span>}
                          {a.teams_sent_at && <span style={{ color: "#6366f1" }}>Teams ✓</span>}
                          {a.email_sent_at && <span style={{ color: "#2dd4bf" }}>Email ✓</span>}
                        </div>
                      </div>
                      <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                        <a
                          href={`https://api.whatsapp.com/send?text=${encodeURIComponent(waMessage)}`}
                          target="_blank"
                          rel="noreferrer"
                          title="Open pre-formatted alert directly in WhatsApp"
                          style={{
                            background: "rgba(34,197,94,0.15)", border: "1px solid rgba(34,197,94,0.4)",
                            color: "#4ade80", padding: "6px 12px", borderRadius: "8px", fontSize: "11px",
                            fontWeight: 700, textDecoration: "none", display: "inline-flex", alignItems: "center", gap: "4px",
                            cursor: "pointer"
                          }}
                        >
                          💬 WhatsApp
                        </a>
                        {!a.is_resolved && (
                          <button onClick={() => handleResolve(a.id)} style={{
                            background: "rgba(34,197,94,0.12)", border: "1px solid rgba(34,197,94,0.3)",
                            color: "#4ade80", padding: "6px 14px", borderRadius: "8px", fontSize: "11px",
                            fontWeight: 700, cursor: "pointer", whiteSpace: "nowrap",
                          }}>✓ Resolve</button>
                        )}
                      </div>
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
                    {malware.map((m) => (
                      <tr key={m.id}>
                        <td style={{ fontWeight: 700, color: "#f1f5f9" }}>{m.server_name || "Unknown"}</td>
                        <td>
                          <span style={{ background: "rgba(248,113,113,0.15)", color: "#f87171", padding: "2px 8px", borderRadius: "8px", fontSize: "10px", fontWeight: 800 }}>
                            {m.threat_type}
                          </span>
                        </td>
                        <td style={{ fontFamily: "monospace", fontSize: "11px", color: "#94a3b8" }}>{m.file_path || "N/A"}</td>
                        <td>
                          <span style={{ background: "rgba(248,113,113,0.2)", color: "#f87171", padding: "2px 8px", borderRadius: "8px", fontSize: "10px", fontWeight: 800 }}>
                            {m.severity.toUpperCase()}
                          </span>
                        </td>
                        <td style={{ maxWidth: "200px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", fontSize: "11px", color: "#64748b" }}>
                          {m.details || "—"}
                        </td>
                        <td style={{ fontSize: "11px", color: "#64748b" }}>{new Date(m.detected_at).toLocaleString()}</td>
                        <td>
                          <button
                            onClick={() => handleResolveMalware(m.id)}
                            style={{
                              background: "rgba(34,197,94,0.12)", border: "1px solid rgba(34,197,94,0.3)",
                              color: "#4ade80", padding: "4px 10px", borderRadius: "6px", fontSize: "10px",
                              fontWeight: 700, cursor: "pointer",
                            }}
                          >
                            ✓ Clear
                          </button>
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
          {/* WhatsApp Card */}
          <div className="card" style={{ border: "1px solid rgba(34,197,94,0.3)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <h3 style={{ fontSize: "16px", fontWeight: 800, color: "#f1f5f9" }}>
                📱 WhatsApp Alert Notifications (User & Group)
              </h3>
              <span className={configStatus.whatsapp_configured ? "badge badge-green" : "badge badge-amber"}>
                {configStatus.whatsapp_configured ? "🟢 Active" : "🟡 Not Configured"}
              </span>
            </div>
            <p style={{ fontSize: "12px", color: "#94a3b8", marginBottom: "16px" }}>
              Automated instant alerts sent to your personal WhatsApp number and team incident response WhatsApp group for downtime, load spikes, and security threats.
            </p>

            <form onSubmit={handleSaveConfig}>
              {/* WhatsApp User Phone */}
              <div style={{ marginBottom: "14px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                  <label style={{ fontSize: "11px", color: "#94a3b8", fontWeight: 700 }}>
                    WHATSAPP USER PHONE NUMBER (DIRECT)
                  </label>
                  {configStatus.whatsapp_user_configured && (
                    <span style={{ fontSize: "10px", color: "#4ade80", fontWeight: 700 }}>✓ Configured</span>
                  )}
                </div>
                <input
                  type="text"
                  className="input-base"
                  placeholder="+1234567890 or +919876543210"
                  value={configForm.whatsapp_user_phone}
                  onChange={(e) => setConfigForm({ ...configForm, whatsapp_user_phone: e.target.value })}
                />
                <p style={{ fontSize: "10px", color: "#64748b", marginTop: "3px" }}>
                  Include international country code (e.g. +91 for India, +1 for US).
                </p>
              </div>

              {/* WhatsApp Group ID / Name */}
              <div style={{ marginBottom: "14px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                  <label style={{ fontSize: "11px", color: "#94a3b8", fontWeight: 700 }}>
                    WHATSAPP GROUP ID OR NAME (INCIDENT TEAM)
                  </label>
                  {configStatus.whatsapp_group_configured && (
                    <span style={{ fontSize: "10px", color: "#4ade80", fontWeight: 700 }}>✓ Configured</span>
                  )}
                </div>
                <input
                  type="text"
                  className="input-base"
                  placeholder="DevOps-Incidents or 120363023456789@g.us"
                  value={configForm.whatsapp_group_id}
                  onChange={(e) => setConfigForm({ ...configForm, whatsapp_group_id: e.target.value })}
                />
                <p style={{ fontSize: "10px", color: "#64748b", marginTop: "3px" }}>
                  Group name for CallMeBot, or Group JID/Chat ID for Green-API/Gateway.
                </p>
              </div>

              {/* Provider Selection */}
              <div style={{ marginBottom: "14px" }}>
                <label style={{ fontSize: "11px", color: "#94a3b8", fontWeight: 700, display: "block", marginBottom: "4px" }}>
                  WHATSAPP DISPATCH ENGINE / PROVIDER
                </label>
                <select
                  value={configForm.whatsapp_provider}
                  onChange={(e) => setConfigForm({ ...configForm, whatsapp_provider: e.target.value })}
                  className="input-base"
                  style={{ cursor: "pointer" }}
                >
                  <option value="callmebot">CallMeBot (Free & Instant — Recommended for Review/Demo)</option>
                  <option value="demo">Demo / Direct Mode (Quick WhatsApp Web Link)</option>
                  <option value="twilio">Twilio WhatsApp API</option>
                  <option value="custom">Custom Gateway (Green-API / UltraMsg / Baileys)</option>
                </select>
              </div>

              {/* Dynamic Credential Fields */}
              {configForm.whatsapp_provider === "callmebot" && (
                <div style={{ marginBottom: "16px", padding: "12px", background: "rgba(15,23,42,0.6)", borderRadius: "8px", border: "1px solid #1e293b" }}>
                  <label style={{ fontSize: "11px", color: "#94a3b8", fontWeight: 700, display: "block", marginBottom: "4px" }}>
                    CALLMEBOT API KEY
                  </label>
                  <input
                    type="password"
                    className="input-base"
                    placeholder="Enter CallMeBot API Key"
                    value={configForm.whatsapp_api_key}
                    onChange={(e) => setConfigForm({ ...configForm, whatsapp_api_key: e.target.value })}
                  />
                  <p style={{ fontSize: "10px", color: "#38bdf8", marginTop: "6px", lineHeight: "1.4" }}>
                    💡 <b>How to get your free key:</b> Add <b>+34 644 14 44 84</b> on WhatsApp and send <i>"I allow callmebot to send me messages"</i>. You'll receive your instant key within 5 seconds.
                  </p>
                </div>
              )}

              {configForm.whatsapp_provider === "twilio" && (
                <div style={{ marginBottom: "16px", padding: "12px", background: "rgba(15,23,42,0.6)", borderRadius: "8px", border: "1px solid #1e293b", display: "grid", gap: "10px" }}>
                  <div>
                    <label style={{ fontSize: "11px", color: "#94a3b8", fontWeight: 700, display: "block", marginBottom: "4px" }}>
                      TWILIO ACCOUNT SID
                    </label>
                    <input
                      type="text"
                      className="input-base"
                      placeholder="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                      value={configForm.whatsapp_account_sid}
                      onChange={(e) => setConfigForm({ ...configForm, whatsapp_account_sid: e.target.value })}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: "11px", color: "#94a3b8", fontWeight: 700, display: "block", marginBottom: "4px" }}>
                      TWILIO AUTH TOKEN
                    </label>
                    <input
                      type="password"
                      className="input-base"
                      placeholder="••••••••••••••••••••••••••••••••"
                      value={configForm.whatsapp_api_key}
                      onChange={(e) => setConfigForm({ ...configForm, whatsapp_api_key: e.target.value })}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: "11px", color: "#94a3b8", fontWeight: 700, display: "block", marginBottom: "4px" }}>
                      TWILIO WHATSAPP SENDER NUMBER
                    </label>
                    <input
                      type="text"
                      className="input-base"
                      placeholder="+14155238886"
                      value={configForm.whatsapp_from_phone}
                      onChange={(e) => setConfigForm({ ...configForm, whatsapp_from_phone: e.target.value })}
                    />
                  </div>
                </div>
              )}

              {configForm.whatsapp_provider === "custom" && (
                <div style={{ marginBottom: "16px", padding: "12px", background: "rgba(15,23,42,0.6)", borderRadius: "8px", border: "1px solid #1e293b", display: "grid", gap: "10px" }}>
                  <div>
                    <label style={{ fontSize: "11px", color: "#94a3b8", fontWeight: 700, display: "block", marginBottom: "4px" }}>
                      GATEWAY / WEBHOOK POST URL
                    </label>
                    <input
                      type="text"
                      className="input-base"
                      placeholder="https://api.green-api.com/waInstance.../sendMessage or custom bot URL"
                      value={configForm.whatsapp_gateway_url}
                      onChange={(e) => setConfigForm({ ...configForm, whatsapp_gateway_url: e.target.value })}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: "11px", color: "#94a3b8", fontWeight: 700, display: "block", marginBottom: "4px" }}>
                      API TOKEN (OPTIONAL)
                    </label>
                    <input
                      type="password"
                      className="input-base"
                      placeholder="Bearer token if required"
                      value={configForm.whatsapp_api_key}
                      onChange={(e) => setConfigForm({ ...configForm, whatsapp_api_key: e.target.value })}
                    />
                  </div>
                </div>
              )}

              <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginTop: "16px" }}>
                <button type="submit" disabled={savingConfig} className="btn-primary" style={{ fontSize: "12px", padding: "8px 16px" }}>
                  {savingConfig ? "Saving..." : "💾 Save WhatsApp Settings"}
                </button>
                <button
                  type="button"
                  onClick={handleTestWaUser}
                  disabled={testingWaUser || !configForm.whatsapp_user_phone}
                  className="btn-secondary"
                  style={{
                    fontSize: "12px", padding: "8px 14px",
                    background: "rgba(34,197,94,0.2)", color: "#4ade80", border: "1px solid rgba(34,197,94,0.4)"
                  }}
                  title="Send immediate test alert to User phone"
                >
                  {testingWaUser ? "Sending..." : "👤 Test User Alert"}
                </button>
                <button
                  type="button"
                  onClick={handleTestWaGroup}
                  disabled={testingWaGroup || !configForm.whatsapp_group_id}
                  className="btn-secondary"
                  style={{
                    fontSize: "12px", padding: "8px 14px",
                    background: "rgba(56,189,248,0.2)", color: "#38bdf8", border: "1px solid rgba(56,189,248,0.4)"
                  }}
                  title="Send immediate test alert to WhatsApp Group"
                >
                  {testingWaGroup ? "Sending..." : "👥 Test Group Alert"}
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
