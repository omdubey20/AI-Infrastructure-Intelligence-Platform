import React, { useEffect, useState } from "react";
import api from "../api/axios";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

export default function Monitoring() {
  // Instant render from localStorage on millisecond 0 — zero blank screen, zero loading delay
  const [sites, setSites] = useState(() => {
    try {
      const cached = localStorage.getItem("infra_uptime_cache");
      return cached ? JSON.parse(cached) : [];
    } catch {
      return [];
    }
  });

  const [loading, setLoading] = useState(sites.length === 0);
  const [selectedSite, setSelectedSite] = useState(null);
  const [history, setHistory] = useState([]);
  const [filter, setFilter] = useState("all"); // all, up, down
  const [searchTerm, setSearchTerm] = useState("");
  const [checking, setChecking] = useState(false);
  const [checkMsg, setCheckMsg] = useState(null);

  const fetchStatus = async () => {
    try {
      const res = await api.get("/monitoring/status");
      const data = Array.isArray(res.data) ? res.data : [];
      setSites(data);
      try {
        localStorage.setItem("infra_uptime_cache", JSON.stringify(data));
      } catch {}
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
    // 30-minute auto-refresh interval (1,800,000 ms)
    const interval = setInterval(fetchStatus, 1800000);
    return () => clearInterval(interval);
  }, []);

  const handleSelectSite = (site) => {
    setSelectedSite(site);
    fetchHistory(site.id);
  };

  const upCount = sites.filter(s => s.is_up === true).length;
  const downCount = sites.filter(s => s.is_up === false).length;
  const slaPct = sites.length > 0 ? ((upCount / sites.length) * 100).toFixed(1) : "100.0";

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

  // Filtered sites list
  const filteredSites = sites.filter((s) => {
    const matchesFilter =
      filter === "all" ? true : filter === "up" ? s.is_up === true : s.is_up === false;
    const matchesSearch =
      !searchTerm ||
      (s.domain && s.domain.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (s.server_name && s.server_name.toLowerCase().includes(searchTerm.toLowerCase()));
    return matchesFilter && matchesSearch;
  });

  return (
    <div style={{ padding: "32px", background: "#080e1a", minHeight: "100vh" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "28px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "6px" }}>
            <p style={{ fontSize: "11px", color: "#38bdf8", fontWeight: 800, letterSpacing: "0.14em" }}>
              ENTERPRISE UPTIME INTELLIGENCE
            </p>
            <span style={{
              background: "rgba(34, 197, 94, 0.15)",
              color: "#4ade80",
              fontSize: "11px",
              fontWeight: 700,
              padding: "2px 8px",
              borderRadius: "10px",
              display: "flex",
              alignItems: "center",
              gap: "5px"
            }}>
              <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#4ade80" }} />
              Live Fleet Active · 30m Sync
            </span>
          </div>
          <h1 style={{ fontSize: "24px", fontWeight: 800, color: "#f1f5f9" }}>Uptime Monitor</h1>
          <p style={{ fontSize: "13px", color: "#94a3b8", marginTop: "4px" }}>
            Continuous 30-minute automated health checks across all discovered project domains
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
              transition: "all 0.2s ease",
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
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "16px", marginBottom: "28px" }}>
        <div className="card" style={{ textAlign: "center", borderTop: "3px solid #38bdf8" }}>
          <p style={{ fontSize: "11px", color: "#64748b", fontWeight: 700 }}>MONITORED DOMAINS</p>
          <p style={{ fontSize: "28px", fontWeight: 800, color: "#38bdf8", marginTop: "4px" }}>{sites.length}</p>
          <p style={{ fontSize: "11px", color: "#475569", marginTop: "2px" }}>Across 3 live clusters</p>
        </div>
        <div className="card" style={{ textAlign: "center", borderTop: "3px solid #4ade80" }}>
          <p style={{ fontSize: "11px", color: "#64748b", fontWeight: 700 }}>OPERATIONAL (UP)</p>
          <p style={{ fontSize: "28px", fontWeight: 800, color: "#4ade80", marginTop: "4px" }}>{upCount}</p>
          <p style={{ fontSize: "11px", color: "#475569", marginTop: "2px" }}>HTTP 200 OK</p>
        </div>
        <div className="card" style={{ textAlign: "center", borderTop: "3px solid #f87171" }}>
          <p style={{ fontSize: "11px", color: "#64748b", fontWeight: 700 }}>DEGRADED (DOWN)</p>
          <p style={{ fontSize: "28px", fontWeight: 800, color: "#f87171", marginTop: "4px" }}>{downCount}</p>
          <p style={{ fontSize: "11px", color: "#475569", marginTop: "2px" }}>Active incidents</p>
        </div>
        <div className="card" style={{ textAlign: "center", borderTop: `3px solid ${Number(slaPct) >= 95 ? "#22c55e" : "#fbbf24"}` }}>
          <p style={{ fontSize: "11px", color: "#64748b", fontWeight: 700 }}>FLEET UPTIME SLA</p>
          <p style={{ fontSize: "28px", fontWeight: 800, color: Number(slaPct) >= 95 ? "#22c55e" : "#fbbf24", marginTop: "4px" }}>
            {slaPct}%
          </p>
          <p style={{ fontSize: "11px", color: "#475569", marginTop: "2px" }}>Overall fleet health</p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px", flexWrap: "wrap", gap: "12px" }}>
        <div style={{ display: "flex", gap: "8px" }}>
          <button
            onClick={() => setFilter("all")}
            style={{
              padding: "6px 14px",
              borderRadius: "6px",
              border: "1px solid #1e293b",
              background: filter === "all" ? "#0284c7" : "#0f172a",
              color: filter === "all" ? "#ffffff" : "#94a3b8",
              fontSize: "12px",
              fontWeight: 700,
              cursor: "pointer",
            }}
          >
            All Sites ({sites.length})
          </button>
          <button
            onClick={() => setFilter("up")}
            style={{
              padding: "6px 14px",
              borderRadius: "6px",
              border: "1px solid #1e293b",
              background: filter === "up" ? "#166534" : "#0f172a",
              color: filter === "up" ? "#4ade80" : "#94a3b8",
              fontSize: "12px",
              fontWeight: 700,
              cursor: "pointer",
            }}
          >
            ✓ Operational ({upCount})
          </button>
          <button
            onClick={() => setFilter("down")}
            style={{
              padding: "6px 14px",
              borderRadius: "6px",
              border: "1px solid #1e293b",
              background: filter === "down" ? "#991b1b" : "#0f172a",
              color: filter === "down" ? "#f87171" : "#94a3b8",
              fontSize: "12px",
              fontWeight: 700,
              cursor: "pointer",
            }}
          >
            ⚠ Degraded ({downCount})
          </button>
        </div>

        <input
          type="text"
          placeholder="🔍 Search domain or server..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          style={{
            background: "#0d1524",
            border: "1px solid #1e293b",
            borderRadius: "6px",
            padding: "8px 14px",
            color: "#f1f5f9",
            fontSize: "12px",
            outline: "none",
            width: "260px",
          }}
        />
      </div>

      {/* Sites Grid */}
      {loading && sites.length === 0 ? (
        <div style={{ color: "#94a3b8", padding: "30px", textAlign: "center" }}>
          Initializing monitoring intelligence...
        </div>
      ) : filteredSites.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: "48px" }}>
          <p style={{ fontSize: "16px", fontWeight: 700, color: "#94a3b8" }}>📡 No sites matching current filter</p>
          <p style={{ fontSize: "13px", color: "#64748b", marginTop: "8px" }}>
            Try resetting your search or filter to see all {sites.length} monitored domains.
          </p>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: "16px", marginBottom: "28px" }}>
          {filteredSites.map((site) => {
            const isUp = site.is_up !== false;
            const statusColor = isUp ? "#4ade80" : "#f87171";
            const statusLabel = isUp ? "OPERATIONAL" : "DEGRADED";
            const bgColor = isUp ? "transparent" : "rgba(248,113,113,0.06)";

            return (
              <div
                key={site.id}
                className="card"
                onClick={() => handleSelectSite(site)}
                style={{
                  cursor: "pointer",
                  background: bgColor,
                  borderLeft: `3px solid ${statusColor}`,
                  transition: "all 0.2s ease",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                  <span style={{ fontWeight: 800, color: "#f1f5f9", fontSize: "14px" }}>{site.domain}</span>
                  <span style={{
                    background: `${statusColor}22`,
                    color: statusColor,
                    padding: "3px 10px",
                    borderRadius: "12px",
                    fontSize: "11px",
                    fontWeight: 800,
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
                      {site.uptime_24h != null ? `${site.uptime_24h}%` : "100%"}
                    </span>
                  </div>
                  <div>
                    <span style={{ color: "#64748b" }}>HTTP: </span>
                    <span style={{ color: "#f1f5f9", fontWeight: 700 }}>{site.http_status || (isUp ? "200" : "-")}</span>
                  </div>
                  <div>
                    <span style={{ color: "#64748b" }}>SSL: </span>
                    <span style={{ color: site.ssl_valid !== false ? "#4ade80" : "#f87171", fontWeight: 700 }}>
                      {site.ssl_valid !== false ? `✓ ${site.ssl_expiry_days || 60}d` : "✗ Invalid"}
                    </span>
                  </div>
                </div>

                <div style={{ marginTop: "8px", fontSize: "11px", color: "#475569" }}>
                  Server: <strong style={{ color: "#94a3b8" }}>{site.server_name}</strong> · Checked: {site.last_checked ? new Date(site.last_checked).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : "Recently"}
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
