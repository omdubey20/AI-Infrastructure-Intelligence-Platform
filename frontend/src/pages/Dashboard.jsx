import React, { useEffect, useState } from "react";
import api from "../api/axios";
import StatCard from "../components/StatCard";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from "recharts";

const HEALTH_COLORS = { Healthy: "#22c55e", Warning: "#f59e0b", Critical: "#f87171" };

const TooltipStyle = {
  contentStyle: {
    background: "#0F1829", border: "1px solid #1E3048",
    color: "#E2E8F0", borderRadius: "8px", fontSize: "12px",
  },
};

function RiskBadge({ score }) {
  if (score >= 70) return <span className="badge badge-red">Critical</span>;
  if (score >= 40) return <span className="badge badge-amber">Warning</span>;
  return <span className="badge badge-green">Healthy</span>;
}

export default function Dashboard() {
  const [scanning, setScanning]       = useState(false);
  const [scanResult, setScanResult]   = useState(null);
  const [lastScanned, setLastScanned] = useState(null);
  const [stats, setStats] = useState({
    total_servers: 0,
    total_projects: 0,
    healthy_servers: 0,
    warning_servers: 0,
    critical_servers: 0,
    top_risk_servers: [],
  });

  const fetchStats = () =>
    api.get("/stats/dashboard").then(r => setStats(r.data)).catch(console.error);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleScan = async () => {
    setScanning(true); setScanResult(null);
    try {
      const res = await api.post("/discovery/scan");
      setScanResult({ ok: true, msg: `Scanned ${res.data.servers_scanned} server(s) successfully` });
      setLastScanned(new Date().toLocaleTimeString());
      fetchStats();
    } catch {
      setScanResult({ ok: false, msg: "Scan failed. Check backend logs." });
    } finally {
      setScanning(false);
    }
  };

  const barData = stats.top_risk_servers.map(s => ({
    name: s.name.length > 12 ? s.name.slice(0, 12) + "..." : s.name,
    CPU:    s.cpu_usage    || 0,
    Memory: s.memory_usage || 0,
    Disk:   s.disk_usage   || 0,
  }));

  const pieData = [
    { name: "Healthy",  value: stats.healthy_servers  || 0 },
    { name: "Warning",  value: stats.warning_servers  || 0 },
    { name: "Critical", value: stats.critical_servers || 0 },
  ].filter(d => d.value > 0);

  return (
    <div style={{ background:"#080e1a", minHeight:"100vh", padding:"0" }}>
      <div style={{ padding:"32px" }}>

        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between",
          alignItems: "flex-start", marginBottom: "28px" }}>
          <div>
            <p style={{ fontSize: "11px", color: "#38bdf8", fontWeight: 700,
              letterSpacing: "0.12em", marginBottom: "6px" }}>INFRASTRUCTURE OVERVIEW</p>
            <h1 style={{ fontSize: "24px", fontWeight: 800, color: "#f1f5f9", marginBottom: "4px" }}>
              Dashboard
            </h1>
            <p style={{ fontSize: "13px", color: "#94a3b8" }}>
              Real-time server health and risk monitoring
            </p>
          </div>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "6px" }}>
            <button onClick={handleScan} disabled={scanning} className="btn-primary" style={{ padding:"12px 28px", fontSize:"15px", fontWeight:800, letterSpacing:"0.03em" }}>
              {scanning
                ? <><span className="spinner" /> Scanning...</>
                : <><span>+</span> Scan All Servers</>}
            </button>
            {lastScanned && (
              <span style={{ fontSize: "11px", color: "#64748b" }}>
                Last scan: {lastScanned}
              </span>
            )}
          </div>
        </div>

        {/* Scan Result Banner */}
        {scanResult && (
          <div className="animate-fadein" style={{
            padding: "12px 16px", borderRadius: "8px", marginBottom: "24px",
            background: scanResult.ok ? "rgba(34,197,94,0.07)" : "rgba(248,113,113,0.07)",
            border: scanResult.ok ? "1px solid rgba(34,197,94,0.25)" : "1px solid rgba(248,113,113,0.25)",
            color: scanResult.ok ? "#4ade80" : "var(--red)",
            fontSize: "13px", display: "flex", alignItems: "center", gap: "8px",
          }}>
            {scanResult.ok ? "OK" : "ERR"} {scanResult.msg}
          </div>
        )}

        {/* Stat Cards */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
          gap: "14px", marginBottom: "28px" }}>
          <div onClick={() => window.location.href="/servers"} style={{cursor:"pointer"}}><StatCard title="Total Servers" value={stats.total_servers} icon="🖥️" color="blue" /></div>
          <div onClick={() => window.location.href="/projects"} style={{cursor:"pointer"}}><StatCard title="Projects" value={stats.total_projects} icon="📁" color="teal" /></div>
          <div onClick={() => window.location.href="/servers"} style={{cursor:"pointer"}}><StatCard title="Healthy" value={stats.healthy_servers} icon="✅" color="green" /></div>
          <div onClick={() => window.location.href="/servers"} style={{cursor:"pointer"}}><StatCard title="Warning" value={stats.warning_servers} icon="⚠️" color="amber" /></div>
          <div onClick={() => window.location.href="/servers"} style={{cursor:"pointer"}}><StatCard title="Critical" value={stats.critical_servers} icon="🔴" color="red" /></div>
        </div>

        {/* Charts Row */}
        {stats.top_risk_servers.length > 0 && (
          <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr",
            gap: "16px", marginBottom: "24px" }}>

            <div className="card">
              <p style={{ fontSize:"13px", fontWeight:700, color:"#94a3b8", letterSpacing:"0.08em", marginBottom:"16px", textTransform:"uppercase" }}>Server Resource Usage</p>
              <ResponsiveContainer width="100%" height={210}>
                <BarChart data={barData} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
                  <XAxis dataKey="name" tick={{ fill: "#64748b", fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: "#64748b", fontSize: 11 }} domain={[0, 100]} axisLine={false} tickLine={false} />
                  <Tooltip {...TooltipStyle} />
                  <Legend wrapperStyle={{ color: "#64748b", fontSize: 11 }} />
                  <Bar dataKey="CPU"    fill="#38BDF8" radius={[4,4,0,0]} />
                  <Bar dataKey="Memory" fill="#2DD4BF" radius={[4,4,0,0]} />
                  <Bar dataKey="Disk"   fill="#F59E0B" radius={[4,4,0,0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="card">
              <p style={{ fontSize:"13px", fontWeight:700, color:"#94a3b8", letterSpacing:"0.08em", marginBottom:"16px", textTransform:"uppercase" }}>Health Distribution</p>
              {pieData.length > 0 ? (
                <ResponsiveContainer width="100%" height={210}>
                  <PieChart>
                    <Pie data={pieData} cx="50%" cy="50%"
                      innerRadius={55} outerRadius={82}
                      paddingAngle={4} dataKey="value">
                      {pieData.map((entry, i) => (
                        <Cell key={i} fill={HEALTH_COLORS[entry.name]} />
                      ))}
                    </Pie>
                    <Tooltip {...TooltipStyle} />
                    <Legend wrapperStyle={{ color: "#64748b", fontSize: 11 }} />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <p style={{ color: "#64748b", fontSize: "13px", marginTop: "16px" }}>
                  Run a scan to see data
                </p>
              )}
            </div>
          </div>
        )}

        {/* Top Risk Servers */}
        <div className="card">
          <p style={{ fontSize:"13px", fontWeight:700, color:"#94a3b8", letterSpacing:"0.08em", marginBottom:"16px", textTransform:"uppercase" }}>Top Risk Servers</p>
          {stats.top_risk_servers.length === 0 ? (
            <div style={{ textAlign: "center", padding: "40px 0" }}>
              <div style={{ fontSize: "32px", marginBottom: "12px" }}>+</div>
              <p style={{ color: "#94a3b8", fontWeight: 600, marginBottom: "4px" }}>No servers found</p>
              <p style={{ color: "#64748b", fontSize: "13px" }}>
                Click Scan All Servers to discover your infrastructure
              </p>
            </div>
          ) : (
            stats.top_risk_servers.map((server) => (
              <div key={server.id} style={{
                display: "flex", justifyContent: "space-between", alignItems: "center",
                padding: "16px", marginBottom: "10px", borderRadius: "10px",
                background: "#1e293b", border: "1px solid #1e293b",
                transition: "border-color 0.2s",
              }}
                onMouseEnter={e => e.currentTarget.style.borderColor = "var(--border-lit)"}
                onMouseLeave={e => e.currentTarget.style.borderColor = "var(--border)"}
              >
                <div>
                  <div style={{ fontWeight: 700, color: "#f1f5f9", fontSize: "14px", marginBottom: "4px" }}>
                    {server.name}
                  </div>
                  <div style={{ fontSize: "12px", color: "#64748b" }}>{server.ip_address}</div>
                  {server.insights?.map((insight, i) => (
                    <div key={i} style={{ marginTop: "4px", color: "#f59e0b", fontSize: "12px" }}>
                      - {insight}
                    </div>
                  ))}
                </div>
                <div style={{ textAlign: "right", flexShrink: 0, marginLeft: "24px" }}>
                  <div style={{ marginBottom: "6px" }}>
                    <RiskBadge score={server.risk_score} />
                  </div>
                  <div style={{ fontSize: "11px", color: "#64748b", fontWeight: 600, letterSpacing: "0.05em" }}>
                    Risk Score: <span style={{
                      color: server.risk_score >= 70 ? "var(--red)" : server.risk_score >= 40 ? "var(--amber)" : "var(--green)"
                    }}>{server.risk_score}</span>
                  </div>
                  <div style={{ display: "flex", gap: "12px", marginTop: "6px", justifyContent: "flex-end" }}>
                    {[["CPU", server.cpu_usage], ["MEM", server.memory_usage], ["DISK", server.disk_usage]].map(([lbl, val]) => (
                      <div key={lbl} style={{ textAlign: "center" }}>
                        <div style={{ fontSize: "10px", color: "#64748b", marginBottom: "2px" }}>{lbl}</div>
                        <div style={{ fontSize: "12px", fontWeight: 700,
                          color: val >= 80 ? "var(--red)" : val >= 60 ? "var(--amber)" : "var(--txt-2)" }}>
                          {val ?? 0}%
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

      </div>
    </div>
  );
}