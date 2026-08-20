import React, { useEffect, useState } from "react";
import api from "../api/axios";

export default function LogExplorer() {
  const [logs, setLogs] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [levelFilter, setLevelFilter] = useState("ALL");
  const [sourceFilter, setSourceFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [hours, setHours] = useState(24);
  const [selectedLog, setSelectedLog] = useState(null);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const params = { hours, limit: 100 };
      if (levelFilter !== "ALL") params.log_level = levelFilter;
      if (sourceFilter !== "all") params.source = sourceFilter;
      if (search.trim()) params.search = search.trim();

      const res = await api.get("/logs/", { params });
      setLogs(res.data?.logs || []);
      setTotal(res.data?.total || 0);
    } catch (err) {
      console.error("Log fetch error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, 15000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [levelFilter, sourceFilter, hours]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    fetchLogs();
  };

  const getLevelBadge = (level) => {
    const lvl = (level || "INFO").toUpperCase();
    if (lvl === "ERROR" || lvl === "CRITICAL") {
      return <span style={{ padding: "3px 8px", borderRadius: "4px", background: "rgba(239,68,68,0.15)", color: "#ef4444", fontWeight: 700, fontSize: "11px" }}>🔴 ERROR</span>;
    }
    if (lvl === "WARN" || lvl === "WARNING") {
      return <span style={{ padding: "3px 8px", borderRadius: "4px", background: "rgba(245,158,11,0.15)", color: "#f59e0b", fontWeight: 700, fontSize: "11px" }}>🟡 WARN</span>;
    }
    return <span style={{ padding: "3px 8px", borderRadius: "4px", background: "rgba(59,130,246,0.15)", color: "#3b82f6", fontWeight: 700, fontSize: "11px" }}>🔵 INFO</span>;
  };

  return (
    <div style={{ padding: "24px", color: "#f8fafc" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
        <div>
          <h1 style={{ margin: 0, fontSize: "24px", fontWeight: 700, color: "#f8fafc" }}>
            📜 Log Explorer & Error Stream
          </h1>
          <p style={{ margin: "4px 0 0", color: "#94a3b8", fontSize: "14px" }}>
            Datadog/Sentry-style real-time log search, level filtering, and stack trace inspector.
          </p>
        </div>
        <button
          onClick={fetchLogs}
          style={{
            padding: "8px 16px", background: "#3b82f6", color: "#fff", border: "none", borderRadius: "6px",
            fontWeight: 600, cursor: "pointer"
          }}
        >
          🔄 Refresh Stream
        </button>
      </div>

      {/* Filter Bar */}
      <div style={{
        background: "#1e293b", padding: "16px", borderRadius: "10px", border: "1px solid #334155",
        marginBottom: "20px", display: "flex", gap: "12px", flexWrap: "wrap", alignItems: "center"
      }}>
        <form onSubmit={handleSearchSubmit} style={{ flex: 1, minWidth: "240px", display: "flex", gap: "8px" }}>
          <input
            type="text"
            placeholder="Search log messages, keywords, or error codes..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              flex: 1, padding: "8px 12px", background: "#0f172a", border: "1px solid #334155",
              color: "#f8fafc", borderRadius: "6px", fontSize: "13px"
            }}
          />
          <button type="submit" style={{ padding: "8px 14px", background: "#3b82f6", color: "#fff", border: "none", borderRadius: "6px", cursor: "pointer" }}>
            Search
          </button>
        </form>

        <select
          value={levelFilter}
          onChange={(e) => setLevelFilter(e.target.value)}
          style={{ padding: "8px 12px", background: "#0f172a", border: "1px solid #334155", color: "#f8fafc", borderRadius: "6px", fontSize: "13px" }}
        >
          <option value="ALL">All Levels</option>
          <option value="ERROR">🔴 ERROR</option>
          <option value="WARN">🟡 WARN</option>
          <option value="INFO">🔵 INFO</option>
        </select>

        <select
          value={sourceFilter}
          onChange={(e) => setSourceFilter(e.target.value)}
          style={{ padding: "8px 12px", background: "#0f172a", border: "1px solid #334155", color: "#f8fafc", borderRadius: "6px", fontSize: "13px" }}
        >
          <option value="all">All Sources</option>
          <option value="syslog">syslog</option>
          <option value="nginx">nginx</option>
          <option value="apache">apache</option>
          <option value="app">application</option>
          <option value="auth">auth</option>
        </select>

        <select
          value={hours}
          onChange={(e) => setHours(Number(e.target.value))}
          style={{ padding: "8px 12px", background: "#0f172a", border: "1px solid #334155", color: "#f8fafc", borderRadius: "6px", fontSize: "13px" }}
        >
          <option value={1}>Last 1 Hour</option>
          <option value={24}>Last 24 Hours</option>
          <option value={168}>Last 7 Days</option>
        </select>
      </div>

      {/* Log Feed */}
      <div style={{ background: "#0f172a", borderRadius: "10px", border: "1px solid #1e293b", padding: "16px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "12px", fontSize: "12px", color: "#64748b" }}>
          <span>Total Streamed Logs: <strong>{total}</strong></span>
          <span>Showing latest 100 entries</span>
        </div>

        {loading ? (
          <div style={{ padding: "40px", textAlign: "center", color: "#94a3b8" }}>Loading log stream...</div>
        ) : logs.length === 0 ? (
          <div style={{ padding: "40px", textAlign: "center", color: "#64748b" }}>
            No log entries found for the selected filter criteria.
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            {logs.map((log) => (
              <div
                key={log.id}
                onClick={() => setSelectedLog(log)}
                style={{
                  background: "#1e293b", padding: "10px 14px", borderRadius: "6px",
                  borderLeft: `4px solid ${log.log_level === "ERROR" ? "#ef4444" : log.log_level === "WARN" ? "#f59e0b" : "#3b82f6"}`,
                  display: "flex", alignItems: "center", gap: "12px", cursor: "pointer",
                  fontFamily: "monospace", fontSize: "12px"
                }}
              >
                <div style={{ width: "140px", color: "#64748b", flexShrink: 0 }}>
                  {new Date(log.timestamp).toLocaleString()}
                </div>
                <div style={{ width: "90px", flexShrink: 0 }}>
                  {getLevelBadge(log.log_level)}
                </div>
                <div style={{ width: "90px", color: "#a855f7", fontWeight: 600, flexShrink: 0 }}>
                  [{log.source}]
                </div>
                <div style={{ width: "120px", color: "#94a3b8", flexShrink: 0 }}>
                  🖥️ {log.server_name}
                </div>
                <div style={{ flex: 1, color: "#f1f5f9", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                  {log.message}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Log Detail Modal */}
      {selectedLog && (
        <div style={{
          position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(0,0,0,0.75)",
          display: "flex", justifyContent: "center", alignItems: "center", zIndex: 1000
        }}>
          <div style={{
            background: "#1e293b", width: "700px", maxWidth: "90%", padding: "24px",
            borderRadius: "12px", border: "1px solid #334155", color: "#f8fafc"
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <h3 style={{ margin: 0, fontSize: "18px" }}>Log Entry Details #{selectedLog.id}</h3>
              <button
                onClick={() => setSelectedLog(null)}
                style={{ background: "none", border: "none", color: "#94a3b8", fontSize: "20px", cursor: "pointer" }}
              >
                ✕
              </button>
            </div>
            <div style={{ display: "flex", gap: "12px", marginBottom: "16px" }}>
              {getLevelBadge(selectedLog.log_level)}
              <span style={{ color: "#a855f7" }}>Source: {selectedLog.source}</span>
              <span style={{ color: "#94a3b8" }}>Server: {selectedLog.server_name}</span>
            </div>
            <div style={{ background: "#0f172a", padding: "12px", borderRadius: "6px", fontFamily: "monospace", fontSize: "12px", marginBottom: "16px", color: "#38bdf8" }}>
              {selectedLog.message}
            </div>
            {selectedLog.raw_data && (
              <pre style={{ background: "#0f172a", padding: "12px", borderRadius: "6px", fontSize: "11px", color: "#cbd5e1", overflowX: "auto" }}>
                {JSON.stringify(selectedLog.raw_data, null, 2)}
              </pre>
            )}
            <div style={{ textAlign: "right", marginTop: "16px" }}>
              <button
                onClick={() => setSelectedLog(null)}
                style={{ padding: "8px 16px", background: "#334155", color: "#fff", border: "none", borderRadius: "6px", cursor: "pointer" }}
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
