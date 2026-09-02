import React, { useEffect, useState } from "react";
import api from "../api/axios";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

export default function Monitoring() {
  const [sites, setSites] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedSite, setSelectedSite] = useState(null);
  const [history, setHistory] = useState([]);

  const fetchStatus = async () => {
    try {
      const res = await api.get("/monitoring/status");
      if (Array.isArray(res.data)) {
        setSites(prev => (res.data.length > 0 || prev.length === 0 ? res.data : prev));
      }
    } catch (e) {
      console.error("Monitoring fetch error:", e);
    } finally {
      setLoading(false);
    }
  };

  const fetchHistory = async (siteId) => {
    try {
      const res = await api.get(`/monitoring/history/${siteId}?hours=24`);
      setHistory(Array.isArray(res.data) ? res.data : []);
    } catch (e) {
      console.error("History fetch error:", e);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 300000);
    return () => clearInterval(interval);
  }, []);

  const handleSelectSite = (site) => {
    setSelectedSite(site);
    fetchHistory(site.id);
  };

  const upCount = sites.filter(s => s.is_up === true).length;
  const downCount = sites.filter(s => s.is_up === false).length;
  const unknownCount = sites.filter(s => s.is_up === null).length;

  const [checking, setChecking] = useState(false);
  const [checkMsg, setCheckMsg] = useState(null);

  const handleRunChecks = async () => {
    setChecking(true);
    setCheckMsg("📡 Probing all sites in parallel (~25s)...");
    try {
      await api.post("/monitoring/check-now");
      let attempts = 0;
      const poll = setInterval(async () => {
        attempts++;
        await fetchStatus();
        if (attempts >= 10) {
          clearInterval(poll);
          setChecking(false);
          setCheckMsg("✓ Latest live check completed!");
          setTimeout(() => setCheckMsg(null), 5000);
        }
      }, 3000);
    } catch (e) {
      console.error("Check trigger error:", e);
      setChecking(false);
      setCheckMsg(null);
    }
  };

  return (
    <div style={{ padding: "32px", background: "#080e1a", minHeight: "100vh" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "28px" }}>
        <div>
          <p style={{ fontSize: "11px", color: "#38bdf8", fontWeight: 800, letterSpacing: "0.14em", marginBottom: "6px" }}>
            WEBSITE UPTIME MONITORING
          </p>
          <h1 style={{ fontSize: "24px", fontWeight: 800, color: "#f1f5f9" }}>Uptime Monitor</h1>
          <p style={{ fontSize: "13px", color: "#94a3b8", marginTop: "4px" }}>
            Real-time HTTP health checks across all discovered project domains
          </p>
        </div>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "8px" }}>
          <button
            onClick={handleRunChecks}
            disabled={checking}
            style={{
              background: checking ? "#334155" : "linear-gradient(135deg, #0284c7 0%, #0369a1 100%)",
              color: "#fff",
              border: "none",
              borderRadius: "8px",
              padding: "10px 18px",
              fontWeight: 700,
              fontSize: "13px",
              cursor: checking ? "not-allowed" : "pointer",
              boxShadow: "0 4px 14px rgba(2, 132, 199, 0.3)",
              display: "flex",
              alignItems: "center",
              gap: "8px",
            }}
          >
            {checking ? "📡 Probing 108 Sites (~25s)..." : "⚡ Run Uptime Checks Now"}
          </button>
          {checkMsg && (
            <span style={{ fontSize: "12px", color: checkMsg.includes("✓") ? "#4ade80" : "#38bdf8", fontWeight: 700 }}>
              {checkMsg}
            </span>
          )}
        </div>
      </div>

      {/* Summary Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: "16px", marginBottom: "28px" }}>
        <div className="card" style={{ textAlign: "center" }}>
          <p style={{ fontSize: "11px", color: "#64748b", fontWeight: 700 }}>MONITORED</p>
          <p style={{ fontSize: "28px", fontWeight: 800, color: "#38bdf8" }}>{sites.length}</p>
        </div>
        <div className="card" style={{ textAlign: "center" }}>
          <p style={{ fontSize: "11px", color: "#64748b", fontWeight: 700 }}>UP</p>
          <p style={{ fontSize: "28px", fontWeight: 800, color: "#4ade80" }}>{upCount}</p>
        </div>
        <div className="card" style={{ textAlign: "center" }}>
          <p style={{ fontSize: "11px", color: "#64748b", fontWeight: 700 }}>DOWN</p>
          <p style={{ fontSize: "28px", fontWeight: 800, color: "#f87171" }}>{downCount}</p>
        </div>
        <div className="card" style={{ textAlign: "center" }}>
          <p style={{ fontSize: "11px", color: "#64748b", fontWeight: 700 }}>PENDING</p>
          <p style={{ fontSize: "28px", fontWeight: 800, color: "#94a3b8" }}>{unknownCount}</p>
        </div>
      </div>

      {/* Sites Grid */}
      {loading ? (
        <div style={{ color: "#94a3b8" }}>Loading monitoring data...</div>
      ) : sites.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: "48px" }}>
          <p style={{ fontSize: "16px", fontWeight: 700, color: "#94a3b8" }}>📡 No monitored sites yet</p>
          <p style={{ fontSize: "13px", color: "#64748b", marginTop: "8px" }}>
            Scan your servers first to discover projects. All live project domains will be automatically monitored.
          </p>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: "16px", marginBottom: "28px" }}>
          {sites.map((site) => {
            const isUp = site.is_up;
            const statusColor = isUp === true ? "#4ade80" : isUp === false ? "#f87171" : "#94a3b8";
            const statusLabel = isUp === true ? "UP" : isUp === false ? "DOWN" : "PENDING";
            const bgColor = isUp === false ? "rgba(248,113,113,0.06)" : "transparent";

            return (
              <div
                key={site.id}
                className="card"
                onClick={() => handleSelectSite(site)}
                style={{
                  cursor: "pointer", background: bgColor,
                  borderLeft: `3px solid ${statusColor}`,
                  transition: "all 0.2s ease",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                  <span style={{ fontWeight: 800, color: "#f1f5f9", fontSize: "14px" }}>{site.domain}</span>
                  <span style={{
                    background: `${statusColor}22`, color: statusColor,
                    padding: "3px 10px", borderRadius: "12px", fontSize: "11px", fontWeight: 800,
                  }}>
                    ● {statusLabel}
                  </span>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", fontSize: "12px" }}>
                  <div>
                    <span style={{ color: "#64748b" }}>Response: </span>
                    <span style={{ color: "#f1f5f9", fontWeight: 700 }}>
                      {site.response_time_ms ? `${site.response_time_ms}ms` : "-"}
                    </span>
                  </div>
                  <div>
                    <span style={{ color: "#64748b" }}>Uptime 24h: </span>
                    <span style={{ color: site.uptime_24h >= 99 ? "#4ade80" : site.uptime_24h >= 95 ? "#fbbf24" : "#f87171", fontWeight: 700 }}>
                      {site.uptime_24h != null ? `${site.uptime_24h}%` : "-"}
                    </span>
                  </div>
                  <div>
                    <span style={{ color: "#64748b" }}>HTTP: </span>
                    <span style={{ color: "#f1f5f9", fontWeight: 700 }}>{site.http_status || "-"}</span>
                  </div>
                  <div>
                    <span style={{ color: "#64748b" }}>SSL: </span>
                    <span style={{ color: site.ssl_valid ? "#4ade80" : "#f87171", fontWeight: 700 }}>
                      {site.ssl_valid === true ? `✓ ${site.ssl_expiry_days || "?"}d` : site.ssl_valid === false ? "✗ Invalid" : "-"}
                    </span>
                  </div>
                </div>

                <div style={{ marginTop: "6px", fontSize: "11px", color: "#475569" }}>
                  Server: {site.server_name} · Last check: {site.last_checked ? new Date(site.last_checked).toLocaleTimeString() : "Never"}
                </div>

                {site.error_message && (
                  <div style={{ marginTop: "6px", fontSize: "11px", color: "#f87171", background: "rgba(248,113,113,0.08)", padding: "4px 8px", borderRadius: "4px" }}>
                    {site.error_message}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Response Time Chart for Selected Site */}
      {selectedSite && history.length > 0 && (
        <div className="card">
          <h3 style={{ fontSize: "14px", fontWeight: 800, color: "#f1f5f9", marginBottom: "16px" }}>
            📊 Response Time — {selectedSite.domain} (Last 24h)
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={history.map(h => ({
              time: new Date(h.checked_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
              ms: h.response_time_ms || 0,
              up: h.is_up ? 1 : 0,
            }))}>
              <XAxis dataKey="time" tick={{ fill: "#64748b", fontSize: 10 }} axisLine={false} tickLine={false} interval="preserveStartEnd" />
              <YAxis tick={{ fill: "#64748b", fontSize: 10 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: "#0d1524", border: "1px solid #1d3047", borderRadius: "8px", color: "#f1f5f9" }} />
              <Line type="monotone" dataKey="ms" stroke="#38bdf8" strokeWidth={2} dot={false} name="Response (ms)" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
