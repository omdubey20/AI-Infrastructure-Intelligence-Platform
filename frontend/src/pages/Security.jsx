import React, { useState, useEffect } from "react";
import api from "../api/axios";

export default function Security() {
  const [alerts, setAlerts] = useState([]);
  const [counts, setCounts] = useState({ total_active: 0, critical_count: 0, warning_count: 0 });
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [config, setConfig] = useState({
    teams_webhook_url: "",
    teams_enabled: false,
    email_recipients: "",
    email_enabled: false,
    alert_on_disk_full: true,
    alert_on_website_down: true,
    alert_on_malware: true,
  });
  const [savingConfig, setSavingConfig] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [filter, setFilter] = useState("all"); // all, CRITICAL, WARNING

  const fetchSecurityData = async (isInitial = false) => {
    try {
      if (isInitial) setLoading(true);
      const [alertsRes, cfgRes] = await Promise.all([
        api.get("/security/alerts"),
        api.get("/security/config"),
      ]);
      setAlerts(Array.isArray(alertsRes.data?.alerts) ? alertsRes.data.alerts : []);
      setCounts({
        total_active: alertsRes.data?.total_active || 0,
        critical_count: alertsRes.data?.critical_count || 0,
        warning_count: alertsRes.data?.warning_count || 0,
      });
      if (cfgRes.data) setConfig(cfgRes.data);
    } catch (err) {
      console.error("Failed to load security data:", err);
    } finally {
      if (isInitial) setLoading(false);
    }
  };

  useEffect(() => {
    fetchSecurityData(true);
    const timer = setInterval(() => fetchSecurityData(false), 30000);
    return () => clearInterval(timer);
  }, []);

  const handleScanNow = async () => {
    try {
      setScanning(true);
      await api.post("/security/scan-now");
      await fetchSecurityData();
    } catch (err) {
      console.error("Security scan error:", err);
    } finally {
      setScanning(false);
    }
  };

  const handleResolveAlert = async (id) => {
    try {
      await api.post(`/security/alerts/${id}/resolve`);
      await fetchSecurityData();
    } catch (err) {
      console.error("Failed to resolve alert:", err);
    }
  };

  const handleSaveConfig = async (e) => {
    e.preventDefault();
    try {
      setSavingConfig(true);
      await api.post("/security/config", config);
      setShowConfigModal(false);
    } catch (err) {
      console.error("Failed to save alert settings:", err);
    } finally {
      setSavingConfig(false);
    }
  };

  const handleSendTestAlert = async () => {
    try {
      setTestResult("Dispatching test alerts...");
      const res = await api.post("/security/test-alert?channel=both");
      setTestResult(`Teams: ${res.data.results.teams} | Email: ${res.data.results.email}`);
    } catch (err) {
      setTestResult("Failed to send test alerts");
    }
  };

  const filteredAlerts = alerts.filter((a) => {
    if (filter === "CRITICAL") return a.severity === "CRITICAL";
    if (filter === "WARNING") return a.severity === "WARNING";
    return true;
  });

  return (
    <div style={{ padding: "32px", maxWidth: "1400px", margin: "0 auto", color: "#f1f5f9" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "28px", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "6px" }}>
            <span style={{ fontSize: "24px" }}>🛡️</span>
            <h1 style={{ fontSize: "24px", fontWeight: 800, margin: 0, letterSpacing: "-0.02em" }}>
              Security, Malware & Alerting Center
            </h1>
          </div>
          <p style={{ color: "#94a3b8", fontSize: "14px", margin: 0 }}>
            Automated server disk threshold warnings, exposed sensitive key detector, and Microsoft Teams & Email multi-channel alerting
          </p>
        </div>

        <div style={{ display: "flex", gap: "10px" }}>
          <button
            onClick={() => setShowConfigModal(true)}
            style={{
              background: "#111c2e",
              color: "#38bdf8",
              border: "1px solid rgba(56,189,248,0.3)",
              borderRadius: "8px",
              padding: "10px 16px",
              fontSize: "13px",
              fontWeight: 700,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "8px",
            }}
          >
            <span>⚙️</span>
            <span>Alert Channels (Teams / Email)</span>
          </button>

          <button
            onClick={handleScanNow}
            disabled={scanning}
            style={{
              background: "linear-gradient(135deg, #0d9488, #059669)",
              color: "white",
              border: "none",
              borderRadius: "8px",
              padding: "10px 18px",
              fontSize: "13px",
              fontWeight: 700,
              cursor: scanning ? "not-allowed" : "pointer",
              display: "flex",
              alignItems: "center",
              gap: "8px",
              boxShadow: "0 0 16px rgba(13,148,136,0.3)",
              opacity: scanning ? 0.7 : 1,
            }}
          >
            <span>{scanning ? "⏳" : "🔍"}</span>
            <span>{scanning ? "Auditing Security..." : "Run Security Audit"}</span>
          </button>
        </div>
      </div>

      {/* Summary KPI Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px", marginBottom: "28px" }}>
        <div style={{ background: "#111c2e", border: "1px solid #1d3047", borderRadius: "12px", padding: "20px" }}>
          <div style={{ fontSize: "12px", color: "#64748b", fontWeight: 700, letterSpacing: "0.05em", marginBottom: "8px" }}>CRITICAL RISKS</div>
          <div style={{ fontSize: "28px", fontWeight: 800, color: counts.critical_count > 0 ? "#f87171" : "#4ade80" }}>
            {counts.critical_count}
          </div>
          <div style={{ fontSize: "12px", color: "#94a3b8", marginTop: "4px" }}>Disk &gt;90% / Exposed keys</div>
        </div>

        <div style={{ background: "#111c2e", border: "1px solid #1d3047", borderRadius: "12px", padding: "20px" }}>
          <div style={{ fontSize: "12px", color: "#64748b", fontWeight: 700, letterSpacing: "0.05em", marginBottom: "8px" }}>WARNING ALERTS</div>
          <div style={{ fontSize: "28px", fontWeight: 800, color: counts.warning_count > 0 ? "#fbbf24" : "#4ade80" }}>
            {counts.warning_count}
          </div>
          <div style={{ fontSize: "12px", color: "#94a3b8", marginTop: "4px" }}>Disk &gt;85% / Expiring SSL</div>
        </div>

        <div style={{ background: "#111c2e", border: "1px solid #1d3047", borderRadius: "12px", padding: "20px" }}>
          <div style={{ fontSize: "12px", color: "#64748b", fontWeight: 700, letterSpacing: "0.05em", marginBottom: "8px" }}>TEAMS ALERT CHANNEL</div>
          <div style={{ fontSize: "22px", fontWeight: 800, color: config.teams_enabled ? "#4ade80" : "#64748b" }}>
            {config.teams_enabled ? "ACTIVE 🟢" : "DISABLED ⚪"}
          </div>
          <div style={{ fontSize: "12px", color: "#94a3b8", marginTop: "4px" }}>Adaptive Card Webhook</div>
        </div>

        <div style={{ background: "#111c2e", border: "1px solid #1d3047", borderRadius: "12px", padding: "20px" }}>
          <div style={{ fontSize: "12px", color: "#64748b", fontWeight: 700, letterSpacing: "0.05em", marginBottom: "8px" }}>EMAIL ALERT CHANNEL</div>
          <div style={{ fontSize: "22px", fontWeight: 800, color: config.email_enabled ? "#4ade80" : "#64748b" }}>
            {config.email_enabled ? "ACTIVE 🟢" : "DISABLED ⚪"}
          </div>
          <div style={{ fontSize: "12px", color: "#94a3b8", marginTop: "4px" }}>SMTP Dispatcher</div>
        </div>
      </div>

      {/* Filter Tabs */}
      <div style={{ display: "flex", gap: "8px", marginBottom: "16px" }}>
        {[
          { key: "all", label: `All Active Alerts (${counts.total_active})` },
          { key: "CRITICAL", label: `🔴 Critical (${counts.critical_count})` },
          { key: "WARNING", label: `🟡 Warning (${counts.warning_count})` },
        ].map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setFilter(key)}
            style={{
              background: filter === key ? "rgba(56,189,248,0.15)" : "#111c2e",
              border: `1px solid ${filter === key ? "#38bdf8" : "#1d3047"}`,
              color: filter === key ? "#38bdf8" : "#94a3b8",
              padding: "8px 14px",
              borderRadius: "8px",
              fontSize: "13px",
              fontWeight: filter === key ? 700 : 500,
              cursor: "pointer",
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Security Alerts List */}
      <div style={{ background: "#111c2e", border: "1px solid #1d3047", borderRadius: "12px", overflow: "hidden" }}>
        {loading ? (
          <div style={{ padding: "40px", textAlign: "center", color: "#64748b" }}>Loading security alerts...</div>
        ) : filteredAlerts.length === 0 ? (
          <div style={{ padding: "48px 24px", textAlign: "center" }}>
            <div style={{ fontSize: "36px", marginBottom: "12px" }}>✅</div>
            <div style={{ fontSize: "16px", fontWeight: 700, color: "#4ade80", marginBottom: "4px" }}>
              All Infrastructure Postures are Safe
            </div>
            <div style={{ fontSize: "13px", color: "#64748b" }}>
              No critical disk saturation, sensitive leaks, or malware threats detected.
            </div>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column" }}>
            {filteredAlerts.map((a) => (
              <div
                key={a.id}
                style={{
                  padding: "18px 24px",
                  borderBottom: "1px solid #162438",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "flex-start",
                  gap: "16px",
                  background: a.severity === "CRITICAL" ? "rgba(248,113,113,0.03)" : "transparent",
                }}
              >
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "6px" }}>
                    <span
                      style={{
                        padding: "2px 8px",
                        borderRadius: "4px",
                        fontSize: "11px",
                        fontWeight: 800,
                        background: a.severity === "CRITICAL" ? "#ef4444" : "#f59e0b",
                        color: "white",
                      }}
                    >
                      {a.severity}
                    </span>
                    <span style={{ fontWeight: 800, fontSize: "15px", color: "#f1f5f9" }}>{a.title}</span>
                    <span style={{ fontSize: "12px", color: "#64748b" }}>
                      Target: <strong style={{ color: "#94a3b8" }}>{a.target_name}</strong> ({a.target_type})
                    </span>
                  </div>

                  <p style={{ color: "#cbd5e1", fontSize: "13px", margin: "0 0 8px" }}>{a.description}</p>

                  <div style={{ background: "#0d1524", border: "1px solid #1d3047", borderRadius: "6px", padding: "8px 12px", fontSize: "12px", color: "#38bdf8" }}>
                    <strong>💡 Recommendation:</strong> {a.recommendation}
                  </div>
                </div>

                <button
                  onClick={() => handleResolveAlert(a.id)}
                  style={{
                    background: "rgba(74,222,128,0.1)",
                    border: "1px solid rgba(74,222,128,0.3)",
                    color: "#4ade80",
                    borderRadius: "6px",
                    padding: "8px 12px",
                    fontSize: "12px",
                    fontWeight: 700,
                    cursor: "pointer",
                    whiteSpace: "nowrap",
                  }}
                >
                  ✓ Mark Resolved
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Alert Channel Settings Modal */}
      {showConfigModal && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: "20px" }}>
          <div style={{ background: "#111c2e", border: "1px solid #2b4565", borderRadius: "16px", padding: "32px", maxWidth: "580px", width: "100%" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
              <h2 style={{ fontSize: "18px", fontWeight: 800, margin: 0 }}>⚙️ Alert Channels (Teams & Email)</h2>
              <button onClick={() => setShowConfigModal(false)} style={{ background: "none", border: "none", color: "#94a3b8", fontSize: "20px", cursor: "pointer" }}>✕</button>
            </div>

            <form onSubmit={handleSaveConfig}>
              {/* Teams Webhook */}
              <div style={{ marginBottom: "18px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                  <label style={{ fontSize: "13px", fontWeight: 700, color: "#94a3b8" }}>Microsoft Teams Incoming Webhook URL</label>
                  <label style={{ fontSize: "12px", color: "#38bdf8", display: "flex", alignItems: "center", gap: "6px", cursor: "pointer" }}>
                    <input
                      type="checkbox"
                      checked={config.teams_enabled}
                      onChange={(e) => setConfig({ ...config, teams_enabled: e.target.checked })}
                    />
                    Enable Teams Alerts
                  </label>
                </div>
                <input
                  type="url"
                  placeholder="https://outlook.office.com/webhook/..."
                  value={config.teams_webhook_url || ""}
                  onChange={(e) => setConfig({ ...config, teams_webhook_url: e.target.value })}
                  style={{ width: "100%", background: "#0d1524", border: "1px solid #1d3047", borderRadius: "8px", padding: "10px", color: "white", fontSize: "13px" }}
                />
              </div>

              {/* Email Alerts */}
              <div style={{ marginBottom: "24px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                  <label style={{ fontSize: "13px", fontWeight: 700, color: "#94a3b8" }}>Email Alert Recipients (comma-separated)</label>
                  <label style={{ fontSize: "12px", color: "#38bdf8", display: "flex", alignItems: "center", gap: "6px", cursor: "pointer" }}>
                    <input
                      type="checkbox"
                      checked={config.email_enabled}
                      onChange={(e) => setConfig({ ...config, email_enabled: e.target.checked })}
                    />
                    Enable Email Alerts
                  </label>
                </div>
                <input
                  type="text"
                  placeholder="devops@company.com, admin@company.com"
                  value={config.email_recipients || ""}
                  onChange={(e) => setConfig({ ...config, email_recipients: e.target.value })}
                  style={{ width: "100%", background: "#0d1524", border: "1px solid #1d3047", borderRadius: "8px", padding: "10px", color: "white", fontSize: "13px" }}
                />
              </div>

              {testResult && (
                <div style={{ background: "#0d1524", border: "1px solid #1d3047", borderRadius: "8px", padding: "10px", fontSize: "12px", color: "#38bdf8", marginBottom: "16px" }}>
                  ℹ️ {testResult}
                </div>
              )}

              <div style={{ display: "flex", justifyContent: "space-between", gap: "10px" }}>
                <button
                  type="button"
                  onClick={handleSendTestAlert}
                  style={{
                    background: "rgba(56,189,248,0.1)",
                    border: "1px solid rgba(56,189,248,0.3)",
                    color: "#38bdf8",
                    borderRadius: "8px",
                    padding: "10px 14px",
                    fontSize: "13px",
                    fontWeight: 700,
                    cursor: "pointer",
                  }}
                >
                  🚀 Send Test Alert
                </button>

                <div style={{ display: "flex", gap: "10px" }}>
                  <button
                    type="button"
                    onClick={() => setShowConfigModal(false)}
                    style={{ background: "#1e293b", border: "none", color: "#94a3b8", borderRadius: "8px", padding: "10px 16px", fontSize: "13px", cursor: "pointer" }}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={savingConfig}
                    style={{
                      background: "linear-gradient(135deg, #0284c7, #2563eb)",
                      border: "none",
                      color: "white",
                      borderRadius: "8px",
                      padding: "10px 20px",
                      fontSize: "13px",
                      fontWeight: 700,
                      cursor: savingConfig ? "not-allowed" : "pointer",
                    }}
                  >
                    {savingConfig ? "Saving..." : "Save Settings"}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
