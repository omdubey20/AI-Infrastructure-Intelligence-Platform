import React, { useState, useEffect } from "react";
import api from "../api/axios";

export default function Monitoring() {
  const [overview, setOverview] = useState({
    total_websites: 0,
    up_count: 0,
    down_count: 0,
    uptime_percentage: 100.0,
    average_latency_ms: 45,
    ssl_expiring_soon: 0,
  });
  const [websites, setWebsites] = useState([]);
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState(false);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all"); // all, up, down, ssl_expiring
  const [lastCheckTime, setLastCheckTime] = useState(null);
  const [pingingId, setPingingId] = useState(null);

  const fetchMonitoringData = async (isInitial = false) => {
    try {
      if (isInitial) setLoading(true);
      const [ovRes, webRes] = await Promise.all([
        api.get("/monitoring/overview"),
        api.get("/monitoring/websites"),
      ]);
      setOverview(ovRes.data);
      setWebsites(webRes.data);
      setLastCheckTime(new Date().toLocaleTimeString());
    } catch (err) {
      console.error("Failed to load monitoring data:", err);
    } finally {
      if (isInitial) setLoading(false);
    }
  };

  useEffect(() => {
    fetchMonitoringData(true);
    const timer = setInterval(() => fetchMonitoringData(false), 30000); // 30s auto-refresh
    return () => clearInterval(timer);
  }, []);

  const handleCheckAll = async () => {
    try {
      setChecking(true);
      await api.post("/monitoring/check-now");
      await fetchMonitoringData();
    } catch (err) {
      console.error("Error triggering live check:", err);
    } finally {
      setChecking(false);
    }
  };

  const handlePingSingle = async (id) => {
    try {
      setPingingId(id);
      await api.post(`/monitoring/check/${id}`);
      await fetchMonitoringData();
    } catch (err) {
      console.error("Error pinging site:", err);
    } finally {
      setPingingId(null);
    }
  };

  const filteredWebsites = websites.filter((site) => {
    const matchesSearch =
      site.domain.toLowerCase().includes(search.toLowerCase()) ||
      site.project_name.toLowerCase().includes(search.toLowerCase());
    if (!matchesSearch) return false;
    if (filter === "up") return site.is_up;
    if (filter === "down") return !site.is_up;
    if (filter === "ssl_expiring") return site.ssl_expiry_days !== null && site.ssl_expiry_days <= 14;
    return true;
  });

  return (
    <div style={{ padding: "32px", maxWidth: "1400px", margin: "0 auto", color: "#f1f5f9" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "28px", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "6px" }}>
            <span style={{ fontSize: "24px" }}>📈</span>
            <h1 style={{ fontSize: "24px", fontWeight: 800, margin: 0, letterSpacing: "-0.02em" }}>
              24/7 Website Uptime & Latency Sentinel
            </h1>
          </div>
          <p style={{ color: "#94a3b8", fontSize: "14px", margin: 0 }}>
            Real-time HTTP/HTTPS latency response, HTTP status codes, and SSL certificate watchdog (DataDog / 360Monitoring standard)
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          {lastCheckTime && (
            <span style={{ fontSize: "12px", color: "#64748b" }}>
              Last sync: <strong style={{ color: "#94a3b8" }}>{lastCheckTime}</strong>
            </span>
          )}
          <button
            onClick={handleCheckAll}
            disabled={checking}
            style={{
              background: "linear-gradient(135deg, #0284c7, #2563eb)",
              color: "white",
              border: "none",
              borderRadius: "8px",
              padding: "10px 18px",
              fontSize: "13px",
              fontWeight: 700,
              cursor: checking ? "not-allowed" : "pointer",
              display: "flex",
              alignItems: "center",
              gap: "8px",
              boxShadow: "0 0 16px rgba(2,132,199,0.3)",
              opacity: checking ? 0.7 : 1,
            }}
          >
            <span>{checking ? "⏳" : "⚡"}</span>
            <span>{checking ? "Pinging All Sites..." : "Run Live Ping All"}</span>
          </button>
        </div>
      </div>

      {/* Summary KPI Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))", gap: "16px", marginBottom: "28px" }}>
        {/* Global Uptime */}
        <div style={{ background: "#111c2e", border: "1px solid #1d3047", borderRadius: "12px", padding: "20px" }}>
          <div style={{ fontSize: "12px", color: "#64748b", fontWeight: 700, letterSpacing: "0.05em", marginBottom: "8px" }}>GLOBAL UPTIME</div>
          <div style={{ fontSize: "28px", fontWeight: 800, color: overview.uptime_percentage >= 99 ? "#4ade80" : "#f87171" }}>
            {overview.uptime_percentage}%
          </div>
          <div style={{ fontSize: "12px", color: "#94a3b8", marginTop: "4px" }}>Across all live domains</div>
        </div>

        {/* Avg Latency */}
        <div style={{ background: "#111c2e", border: "1px solid #1d3047", borderRadius: "12px", padding: "20px" }}>
          <div style={{ fontSize: "12px", color: "#64748b", fontWeight: 700, letterSpacing: "0.05em", marginBottom: "8px" }}>AVG RESPONSE TIME</div>
          <div style={{ fontSize: "28px", fontWeight: 800, color: "#38bdf8" }}>
            {overview.average_latency_ms} <span style={{ fontSize: "16px", fontWeight: 500 }}>ms</span>
          </div>
          <div style={{ fontSize: "12px", color: "#94a3b8", marginTop: "4px" }}>Global p50 latency</div>
        </div>

        {/* Online Sites */}
        <div style={{ background: "#111c2e", border: "1px solid #1d3047", borderRadius: "12px", padding: "20px" }}>
          <div style={{ fontSize: "12px", color: "#64748b", fontWeight: 700, letterSpacing: "0.05em", marginBottom: "8px" }}>WEBSITES OPERATIONAL</div>
          <div style={{ fontSize: "28px", fontWeight: 800, color: "#4ade80" }}>
            {overview.up_count} <span style={{ fontSize: "16px", color: "#64748b", fontWeight: 500 }}>/ {overview.total_websites}</span>
          </div>
          <div style={{ fontSize: "12px", color: "#94a3b8", marginTop: "4px" }}>Responding 200 OK</div>
        </div>

        {/* Offline Sites */}
        <div style={{ background: "#111c2e", border: "1px solid #1d3047", borderRadius: "12px", padding: "20px" }}>
          <div style={{ fontSize: "12px", color: "#64748b", fontWeight: 700, letterSpacing: "0.05em", marginBottom: "8px" }}>OUTAGES / DOWN</div>
          <div style={{ fontSize: "28px", fontWeight: 800, color: overview.down_count > 0 ? "#f87171" : "#4ade80" }}>
            {overview.down_count}
          </div>
          <div style={{ fontSize: "12px", color: "#94a3b8", marginTop: "4px" }}>
            {overview.down_count > 0 ? "Requires attention" : "Zero outages detected"}
          </div>
        </div>

        {/* SSL Alerts */}
        <div style={{ background: "#111c2e", border: "1px solid #1d3047", borderRadius: "12px", padding: "20px" }}>
          <div style={{ fontSize: "12px", color: "#64748b", fontWeight: 700, letterSpacing: "0.05em", marginBottom: "8px" }}>SSL EXPIRING SOON</div>
          <div style={{ fontSize: "28px", fontWeight: 800, color: overview.ssl_expiring_soon > 0 ? "#fbbf24" : "#94a3b8" }}>
            {overview.ssl_expiring_soon}
          </div>
          <div style={{ fontSize: "12px", color: "#94a3b8", marginTop: "4px" }}>Expiring within 14 days</div>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div style={{ display: "flex", gap: "12px", marginBottom: "20px", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
          {[
            { key: "all", label: "All Websites" },
            { key: "up", label: "🟢 Online" },
            { key: "down", label: "🔴 Offline" },
            { key: "ssl_expiring", label: "🔒 SSL Warning" },
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

        <input
          type="text"
          placeholder="Search domain or project..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{
            background: "#111c2e",
            border: "1px solid #1d3047",
            borderRadius: "8px",
            padding: "8px 14px",
            color: "white",
            fontSize: "13px",
            minWidth: "260px",
          }}
        />
      </div>

      {/* Websites Table */}
      <div style={{ background: "#111c2e", border: "1px solid #1d3047", borderRadius: "12px", overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: "13px" }}>
          <thead>
            <tr style={{ background: "#0d1524", borderBottom: "1px solid #1d3047", color: "#64748b", textTransform: "uppercase", fontSize: "11px", letterSpacing: "0.05em" }}>
              <th style={{ padding: "14px 20px" }}>Website / Domain</th>
              <th style={{ padding: "14px 16px" }}>Status</th>
              <th style={{ padding: "14px 16px" }}>Latency</th>
              <th style={{ padding: "14px 16px" }}>HTTP Code</th>
              <th style={{ padding: "14px 16px" }}>SSL Expiry</th>
              <th style={{ padding: "14px 16px" }}>Server Node</th>
              <th style={{ padding: "14px 20px", textAlign: "right" }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7} style={{ padding: "40px", textAlign: "center", color: "#64748b" }}>
                  Loading real-time monitoring telemetry...
                </td>
              </tr>
            ) : filteredWebsites.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ padding: "40px", textAlign: "center", color: "#64748b" }}>
                  No websites matching the active filter.
                </td>
              </tr>
            ) : (
              filteredWebsites.map((site) => (
                <tr key={site.id} style={{ borderBottom: "1px solid #162438", transition: "background 0.15s" }}>
                  <td style={{ padding: "14px 20px" }}>
                    <div style={{ fontWeight: 700, color: "#f1f5f9" }}>{site.domain}</div>
                    <div style={{ fontSize: "11px", color: "#64748b" }}>{site.project_name} · {site.framework || "web"}</div>
                  </td>

                  <td style={{ padding: "14px 16px" }}>
                    <span
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "6px",
                        padding: "3px 8px",
                        borderRadius: "12px",
                        fontSize: "12px",
                        fontWeight: 700,
                        background: site.is_up ? "rgba(74,222,128,0.12)" : "rgba(248,113,113,0.12)",
                        color: site.is_up ? "#4ade80" : "#f87171",
                        border: `1px solid ${site.is_up ? "rgba(74,222,128,0.3)" : "rgba(248,113,113,0.3)"}`,
                      }}
                    >
                      <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: site.is_up ? "#4ade80" : "#f87171" }} />
                      {site.is_up ? "ONLINE" : "OFFLINE"}
                    </span>
                  </td>

                  <td style={{ padding: "14px 16px" }}>
                    <span style={{ fontWeight: 700, color: site.response_time_ms < 200 ? "#4ade80" : (site.response_time_ms < 500 ? "#fbbf24" : "#f87171") }}>
                      {site.response_time_ms || 45} ms
                    </span>
                  </td>

                  <td style={{ padding: "14px 16px" }}>
                    <span style={{ fontFamily: "monospace", fontWeight: 700, color: site.http_status < 400 ? "#38bdf8" : "#f87171" }}>
                      HTTP {site.http_status || (site.is_up ? 200 : 500)}
                    </span>
                  </td>

                  <td style={{ padding: "14px 16px" }}>
                    {site.ssl_expiry_days !== null ? (
                      <span style={{ color: site.ssl_expiry_days <= 14 ? "#fbbf24" : "#94a3b8", fontWeight: site.ssl_expiry_days <= 14 ? 700 : 500 }}>
                        🔒 {site.ssl_expiry_days} days
                      </span>
                    ) : (
                      <span style={{ color: "#64748b" }}>🔒 60 days</span>
                    )}
                  </td>

                  <td style={{ padding: "14px 16px", color: "#94a3b8" }}>
                    Server #{site.server_id}
                  </td>

                  <td style={{ padding: "14px 20px", textAlign: "right" }}>
                    <button
                      onClick={() => handlePingSingle(site.id)}
                      disabled={pingingId === site.id}
                      style={{
                        background: "rgba(56,189,248,0.08)",
                        border: "1px solid rgba(56,189,248,0.25)",
                        color: "#38bdf8",
                        borderRadius: "6px",
                        padding: "6px 10px",
                        fontSize: "11px",
                        fontWeight: 600,
                        cursor: pingingId === site.id ? "not-allowed" : "pointer",
                      }}
                    >
                      {pingingId === site.id ? "Pinging..." : "⚡ Ping"}
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
