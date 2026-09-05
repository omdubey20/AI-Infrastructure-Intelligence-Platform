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
    whatsapp_target: "both",
    whatsapp_phone: "",
    whatsapp_group_id: "",
    whatsapp_provider: "callmebot",
    whatsapp_api_key: "",
    whatsapp_account_sid: "",
    whatsapp_from_phone: "",
    whatsapp_gateway_url: "",
    teams_webhook_url: "",
    email_to: "",
    smtp_host: "",
    smtp_port: 587,
    smtp_user: "",
    smtp_password: ""
  });
  const [configStatus, setConfigStatus] = useState({
    whatsapp_configured: false,
    email_configured: false,
    teams_configured: false
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
        whatsapp_target: res.data.whatsapp_target || "both",
        whatsapp_phone: res.data.whatsapp_phone || "",
        whatsapp_group_id: res.data.whatsapp_group_id || "",
        whatsapp_provider: res.data.whatsapp_provider || "callmebot",
        whatsapp_api_key: res.data.whatsapp_api_key || "",
        whatsapp_account_sid: res.data.whatsapp_account_sid || "",
        whatsapp_from_phone: res.data.whatsapp_from_phone || "",
        whatsapp_gateway_url: res.data.whatsapp_gateway_url || "",
        teams_webhook_url: res.data.teams_webhook_url || "",
        email_to: res.data.email_to || "",
        smtp_host: res.data.smtp_host || "",
        smtp_port: res.data.smtp_port || 587,
        smtp_user: res.data.smtp_user || "",
        smtp_password: res.data.smtp_password || ""
      });
      setConfigStatus({
        whatsapp_configured: res.data.whatsapp_configured,
        email_configured: res.data.email_configured,
        teams_configured: res.data.teams_configured
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
    } catch (err) {
      setActionMsg({ ok: false, msg: err.response?.data?.detail || "WhatsApp user test failed." });
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
      setActionMsg({ ok: false, msg: err.response?.data?.detail || "WhatsApp group test failed." });
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
                          {(a.whatsapp_sent_at || a.teams_sent_at) && (
                            <span style={{ color: "#22c55e", fontWeight: 700, display: "inline-flex", alignItems: "center", gap: "3px" }}>
                              💬 WhatsApp ✓
                            </span>
                          )}
                          {a.email_sent_at && (
                            <span style={{ color: "#2dd4bf", fontWeight: 600, display: "inline-flex", alignItems: "center", gap: "3px" }}>
                              ✉️ Email ✓
                            </span>
                          )}
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
          {/* WhatsApp Card */}
          <div className="card" style={{ border: "1px solid rgba(34,197,94,0.3)", background: "linear-gradient(180deg, rgba(34,197,94,0.04) 0%, rgba(15,23,42,0.6) 100%)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
              <h3 style={{ fontSize: "16px", fontWeight: 800, color: "#f1f5f9", display: "flex", alignItems: "center", gap: "8px" }}>
                <span>💬</span> WhatsApp Alerts (User & Group)
              </h3>
              <span className={configStatus.whatsapp_configured ? "badge badge-green" : "badge badge-amber"}>
                {configStatus.whatsapp_configured ? "🟢 Active" : "🟡 Not Configured"}
              </span>
            </div>
            <p style={{ fontSize: "12px", color: "#94a3b8", marginBottom: "16px", lineHeight: "1.5" }}>
              Deliver instantaneous infrastructure alerts with formatted markdown and diagnostic details directly to an on-call engineer's phone and WhatsApp operations groups.
            </p>

            <form onSubmit={handleSaveConfig}>
              {/* Notification Target Mode */}
              <div style={{ marginBottom: "14px" }}>
                <label style={{ fontSize: "11px", color: "#94a3b8", fontWeight: 700, display: "block", marginBottom: "6px" }}>
                  DISPATCH TARGET
                </label>
                <div style={{ display: "flex", gap: "8px" }}>
                  {[
                    { id: "both", label: "👥 Both User & Group" },
                    { id: "user", label: "📱 User Only" },
                    { id: "group", label: "📢 Group Only" },
                  ].map((t) => (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => setConfigForm({ ...configForm, whatsapp_target: t.id })}
                      style={{
                        flex: 1,
                        padding: "7px 8px",
                        borderRadius: "8px",
                        fontSize: "11px",
                        fontWeight: 700,
                        cursor: "pointer",
                        border: configForm.whatsapp_target === t.id ? "1px solid #22c55e" : "1px solid #1e293b",
                        background: configForm.whatsapp_target === t.id ? "rgba(34,197,94,0.15)" : "#0b1329",
                        color: configForm.whatsapp_target === t.id ? "#4ade80" : "#94a3b8",
                      }}
                    >
                      {t.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Phone & Group Grid */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", marginBottom: "14px" }}>
                <div>
                  <label style={{ fontSize: "11px", color: "#94a3b8", fontWeight: 700, display: "block", marginBottom: "4px" }}>
                    USER PHONE NUMBER
                  </label>
                  <input
                    type="text"
                    className="input-base"
                    placeholder="+919876543210"
                    value={configForm.whatsapp_phone}
                    onChange={(e) => setConfigForm({ ...configForm, whatsapp_phone: e.target.value })}
                  />
                  <span style={{ fontSize: "10px", color: "#64748b" }}>With country code (+91, +1, etc.)</span>
                </div>
                <div>
                  <label style={{ fontSize: "11px", color: "#94a3b8", fontWeight: 700, display: "block", marginBottom: "4px" }}>
                    GROUP ID / CHAT REF
                  </label>
                  <input
                    type="text"
                    className="input-base"
                    placeholder="120363024567890@g.us or Ops-Team"
                    value={configForm.whatsapp_group_id}
                    onChange={(e) => setConfigForm({ ...configForm, whatsapp_group_id: e.target.value })}
                  />
                  <span style={{ fontSize: "10px", color: "#64748b" }}>WhatsApp group JID or link identifier</span>
                </div>
              </div>

              {/* API Provider Selector */}
              <div style={{ marginBottom: "14px" }}>
                <label style={{ fontSize: "11px", color: "#94a3b8", fontWeight: 700, display: "block", marginBottom: "4px" }}>
                  WHATSAPP API PROVIDER
                </label>
                <select
                  value={configForm.whatsapp_provider}
                  onChange={(e) => setConfigForm({ ...configForm, whatsapp_provider: e.target.value })}
                  className="input-base"
                  style={{ cursor: "pointer", background: "#0b1329" }}
                >
                  <option value="callmebot">CallMeBot (Free, Instant Setup — Zero Verification)</option>
                  <option value="demo">Interactive Demo / Simulator Mode (Test Live Without Keys)</option>
                  <option value="twilio">Twilio WhatsApp Business</option>
                  <option value="cloud_api">Meta WhatsApp Cloud API / Custom Gateway</option>
                </select>
              </div>

              {/* Provider-specific fields */}
              {configForm.whatsapp_provider === "callmebot" && (
                <div style={{ marginBottom: "14px" }}>
                  <label style={{ fontSize: "11px", color: "#94a3b8", fontWeight: 700, display: "block", marginBottom: "4px" }}>
                    CALLMEBOT API KEY
                  </label>
                  <input
                    type="password"
                    className="input-base"
                    placeholder="Enter CallMeBot API key"
                    value={configForm.whatsapp_api_key}
                    onChange={(e) => setConfigForm({ ...configForm, whatsapp_api_key: e.target.value })}
                  />
                  <span style={{ fontSize: "10px", color: "#64748b" }}>
                    Free key: Text <i>"I allow callmebot to send me messages"</i> to <b>+34 644 44 49 64</b> on WhatsApp.
                  </span>
                </div>
              )}

              {configForm.whatsapp_provider === "twilio" && (
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", marginBottom: "14px" }}>
                  <div>
                    <label style={{ fontSize: "11px", color: "#94a3b8", fontWeight: 700, display: "block", marginBottom: "4px" }}>
                      TWILIO ACCOUNT SID
                    </label>
                    <input
                      type="text"
                      className="input-base"
                      placeholder="ACxxxxxxxx..."
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
                      placeholder="••••••••"
                      value={configForm.whatsapp_api_key}
                      onChange={(e) => setConfigForm({ ...configForm, whatsapp_api_key: e.target.value })}
                    />
                  </div>
                  <div style={{ gridColumn: "span 2" }}>
                    <label style={{ fontSize: "11px", color: "#94a3b8", fontWeight: 700, display: "block", marginBottom: "4px" }}>
                      TWILIO FROM NUMBER
                    </label>
                    <input
                      type="text"
                      className="input-base"
                      placeholder="whatsapp:+14155238886"
                      value={configForm.whatsapp_from_phone}
                      onChange={(e) => setConfigForm({ ...configForm, whatsapp_from_phone: e.target.value })}
                    />
                  </div>
                </div>
              )}

              {configForm.whatsapp_provider === "cloud_api" && (
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", marginBottom: "14px" }}>
                  <div>
                    <label style={{ fontSize: "11px", color: "#94a3b8", fontWeight: 700, display: "block", marginBottom: "4px" }}>
                      PHONE NUMBER ID
                    </label>
                    <input
                      type="text"
                      className="input-base"
                      placeholder="Meta Phone Number ID"
                      value={configForm.whatsapp_account_sid}
                      onChange={(e) => setConfigForm({ ...configForm, whatsapp_account_sid: e.target.value })}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: "11px", color: "#94a3b8", fontWeight: 700, display: "block", marginBottom: "4px" }}>
                      ACCESS TOKEN
                    </label>
                    <input
                      type="password"
                      className="input-base"
                      placeholder="Bearer token"
                      value={configForm.whatsapp_api_key}
                      onChange={(e) => setConfigForm({ ...configForm, whatsapp_api_key: e.target.value })}
                    />
                  </div>
                  <div style={{ gridColumn: "span 2" }}>
                    <label style={{ fontSize: "11px", color: "#94a3b8", fontWeight: 700, display: "block", marginBottom: "4px" }}>
                      CUSTOM GATEWAY URL (OPTIONAL)
                    </label>
                    <input
                      type="text"
                      className="input-base"
                      placeholder="https://api.ultramsg.com/... or self-hosted endpoint"
                      value={configForm.whatsapp_gateway_url}
                      onChange={(e) => setConfigForm({ ...configForm, whatsapp_gateway_url: e.target.value })}
                    />
                  </div>
                </div>
              )}

              {configForm.whatsapp_provider === "demo" && (
                <div style={{ padding: "10px 12px", background: "rgba(34,197,94,0.1)", borderRadius: "8px", border: "1px dashed rgba(34,197,94,0.3)", marginBottom: "14px" }}>
                  <p style={{ margin: 0, fontSize: "11px", color: "#86efac", lineHeight: "1.4" }}>
                    ✨ <b>Demo / Viva Mode:</b> Formats markdown messages and delivers to the internal dispatcher with timestamp tracking. Ideal for testing and live presentations without requiring external SMS API credits.
                  </p>
                </div>
              )}

              {/* Action Buttons */}
              <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                <button
                  type="submit"
                  disabled={savingConfig}
                  className="btn-primary"
                  style={{ fontSize: "12px", padding: "8px 14px", background: "#16a34a", borderColor: "#22c55e" }}
                >
                  {savingConfig ? "Saving..." : "💾 Save WhatsApp"}
                </button>
                <button
                  type="button"
                  onClick={handleTestWaUser}
                  disabled={testingWaUser || !configForm.whatsapp_phone}
                  className="btn-secondary"
                  style={{
                    fontSize: "12px",
                    padding: "8px 12px",
                    background: "rgba(34,197,94,0.15)",
                    color: "#4ade80",
                    border: "1px solid rgba(34,197,94,0.4)",
                    cursor: configForm.whatsapp_phone ? "pointer" : "not-allowed",
                  }}
                  title={!configForm.whatsapp_phone ? "Please enter a user phone number" : "Send test alert to user"}
                >
                  {testingWaUser ? "Sending..." : "📱 Test User"}
                </button>
                <button
                  type="button"
                  onClick={handleTestWaGroup}
                  disabled={testingWaGroup || !configForm.whatsapp_group_id}
                  className="btn-secondary"
                  style={{
                    fontSize: "12px",
                    padding: "8px 12px",
                    background: "rgba(56,189,248,0.15)",
                    color: "#38bdf8",
                    border: "1px solid rgba(56,189,248,0.4)",
                    cursor: configForm.whatsapp_group_id ? "pointer" : "not-allowed",
                  }}
                  title={!configForm.whatsapp_group_id ? "Please enter a group ID" : "Send test alert to group"}
                >
                  {testingWaGroup ? "Sending..." : "👥 Test Group"}
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
