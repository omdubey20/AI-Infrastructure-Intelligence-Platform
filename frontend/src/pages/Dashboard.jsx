import React, { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { useNavigate } from "react-router-dom";
import api from "../api/axios";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend
} from "recharts";

const NAV = [
  { path: "/", icon: "📊", label: "Dashboard" },
  { path: "/servers", icon: "🖥️", label: "Servers" },
  { path: "/projects", icon: "📁", label: "Projects" },
  { path: "/cleanup", icon: "🧹", label: "Cleanup" }
];

const PIE_COLORS = ["#22c55e", "#f59e0b", "#ef4444"];

export default function Dashboard() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [scanning, setScanning] = useState(false);
  const [scanResult, setScanResult] = useState(null);
  const [lastScanned, setLastScanned] = useState(null);
  const [stats, setStats] = useState({
    total_servers: 0,
    total_projects: 0,
    healthy_servers: 0,
    warning_servers: 0,
    critical_servers: 0,
    top_risk_servers: []
  });

  const fetchStats = () => {
    api.get("/stats/dashboard").then((res) => setStats(res.data)).catch(console.error);
  };

  useEffect(() => { fetchStats(); }, []);

  const handleScan = async () => {
    setScanning(true);
    setScanResult(null);
    try {
      const res = await api.post("/discovery/scan");
      setScanResult({ success: true, message: `Scanned ${res.data.servers_scanned} server(s) successfully` });
      setLastScanned(new Date().toLocaleTimeString());
      fetchStats();
    } catch {
      setScanResult({ success: false, message: "Scan failed. Check backend logs." });
    } finally {
      setScanning(false);
    }
  };

  const cards = [
    { label: "Total Servers", value: stats.total_servers, icon: "🖥️", color: "#3b82f6" },
    { label: "Projects", value: stats.total_projects, icon: "📁", color: "#10b981" },
    { label: "Healthy", value: stats.healthy_servers, icon: "✅", color: "#22c55e" },
    { label: "Warnings", value: stats.warning_servers, icon: "⚠️", color: "#f59e0b" },
    { label: "Critical", value: stats.critical_servers, icon: "🚨", color: "#ef4444" }
  ];

  const barData = stats.top_risk_servers.map(s => ({
    name: s.name.length > 12 ? s.name.slice(0, 12) + "…" : s.name,
    CPU: s.cpu_usage || 0,
    Memory: s.memory_usage || 0,
    Disk: s.disk_usage || 0,
  }));

  const pieData = [
    { name: "Healthy", value: stats.healthy_servers || 0 },
    { name: "Warning", value: stats.warning_servers || 0 },
    { name: "Critical", value: stats.critical_servers || 0 },
  ].filter(d => d.value > 0);

  const card = { background: "#1e293b", padding: "24px", borderRadius: "12px", border: "1px solid #334155" };

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "#0f172a" }}>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>

      <aside style={{ width: "250px", background: "#1e293b", padding: "24px 16px", borderRight: "1px solid #334155", flexShrink: 0 }}>
        <h2 style={{ color: "white", marginBottom: "32px", fontSize: "16px", fontWeight: "bold" }}>ServerManager Pro</h2>
        {NAV.map((item) => (
          <div key={item.path} onClick={() => navigate(item.path)}
            style={{ padding: "12px", marginBottom: "8px", borderRadius: "8px", cursor: "pointer",
              color: window.location.pathname === item.path ? "white" : "#94a3b8",
              background: window.location.pathname === item.path ? "#2563eb" : "transparent" }}>
            {item.icon} {item.label}
          </div>
        ))}
        <div onClick={() => { logout(); navigate("/login"); }}
          style={{ marginTop: "40px", color: "#ef4444", cursor: "pointer", padding: "12px" }}>
          🚪 Logout
        </div>
      </aside>

      <main style={{ flex: 1, padding: "32px", overflowY: "auto" }}>

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "24px" }}>
          <div>
            <h1 style={{ color: "white", marginBottom: "4px", fontSize: "26px", fontWeight: "bold" }}>
              Infrastructure Dashboard
            </h1>
            <p style={{ color: "#94a3b8", margin: 0 }}>Real-time server health and risk monitoring</p>
          </div>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "6px" }}>
            <button onClick={handleScan} disabled={scanning}
              style={{ background: scanning ? "#1e3a5f" : "#2563eb", color: "white", border: "none",
                padding: "12px 24px", borderRadius: "8px", cursor: scanning ? "not-allowed" : "pointer",
                fontWeight: "600", fontSize: "14px", display: "flex", alignItems: "center", gap: "8px" }}>
              {scanning ? (
                <>
                  <span style={{ display: "inline-block", width: "14px", height: "14px",
                    border: "2px solid white", borderTopColor: "transparent", borderRadius: "50%",
                    animation: "spin 0.8s linear infinite" }} />
                  Scanning...
                </>
              ) : "🔍 Scan All Servers"}
            </button>
            {lastScanned && (
              <span style={{ color: "#64748b", fontSize: "12px" }}>Last scanned: {lastScanned}</span>
            )}
          </div>
        </div>

        {scanResult && (
          <div style={{ padding: "12px 16px", borderRadius: "8px", marginBottom: "24px",
            background: scanResult.success ? "#052e16" : "#2d0a0a",
            border: `1px solid ${scanResult.success ? "#16a34a" : "#dc2626"}`,
            color: scanResult.success ? "#4ade80" : "#f87171", fontSize: "14px" }}>
            {scanResult.success ? "✅" : "❌"} {scanResult.message}
          </div>
        )}

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(160px,1fr))", gap: "16px", marginBottom: "28px" }}>
          {cards.map((c) => (
            <div key={c.label} style={card}>
              <div style={{ fontSize: "26px", marginBottom: "8px" }}>{c.icon}</div>
              <div style={{ color: "#94a3b8", fontSize: "13px" }}>{c.label}</div>
              <div style={{ color: c.color, fontSize: "32px", fontWeight: "bold" }}>{c.value}</div>
            </div>
          ))}
        </div>

        {stats.top_risk_servers.length > 0 && (
          <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "20px", marginBottom: "28px" }}>
            <div style={card}>
              <h3 style={{ color: "white", marginBottom: "16px", fontSize: "15px", fontWeight: "600" }}>
                📊 Server Resource Usage
              </h3>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={barData} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
                  <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 12 }} />
                  <YAxis tick={{ fill: "#94a3b8", fontSize: 12 }} domain={[0, 100]} />
                  <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155", color: "white", borderRadius: "8px" }} />
                  <Legend wrapperStyle={{ color: "#94a3b8", fontSize: 12 }} />
                  <Bar dataKey="CPU" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="Memory" fill="#10b981" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="Disk" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div style={card}>
              <h3 style={{ color: "white", marginBottom: "16px", fontSize: "15px", fontWeight: "600" }}>
                🟢 Server Health
              </h3>
              {pieData.length > 0 ? (
                <ResponsiveContainer width="100%" height={220}>
                  <PieChart>
                    <Pie data={pieData} cx="50%" cy="50%" innerRadius={55} outerRadius={85}
                      paddingAngle={4} dataKey="value">
                      {pieData.map((entry, index) => (
                        <Cell key={index} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155", color: "white", borderRadius: "8px" }} />
                    <Legend wrapperStyle={{ color: "#94a3b8", fontSize: 12 }} />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <p style={{ color: "#94a3b8", fontSize: "13px" }}>Run a scan to see health data</p>
              )}
            </div>
          </div>
        )}

        <div style={card}>
          <h2 style={{ color: "white", marginBottom: "20px", fontSize: "16px", fontWeight: "600" }}>
            🚨 Top Risk Servers
          </h2>
          {stats.top_risk_servers.length === 0 ? (
            <p style={{ color: "#94a3b8" }}>No servers found. Click Scan All Servers to discover.</p>
          ) : (
            stats.top_risk_servers.map((server) => (
              <div key={server.id} style={{ padding: "16px", marginBottom: "12px", borderRadius: "10px",
                background: "#0f172a", border: "1px solid #334155" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div>
                    <div style={{ color: "white", fontWeight: "bold", fontSize: "15px" }}>{server.name}</div>
                    <div style={{ color: "#94a3b8", fontSize: "13px" }}>{server.ip_address}</div>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <div style={{ color: server.risk_score >= 70 ? "#ef4444" : server.risk_score >= 40 ? "#f59e0b" : "#22c55e",
                      fontWeight: "bold", fontSize: "16px" }}>
                      Risk {server.risk_score}
                    </div>
                    <div style={{ display: "flex", gap: "8px", marginTop: "4px", justifyContent: "flex-end" }}>
                      <span style={{ fontSize: "11px", color: "#64748b" }}>CPU: {server.cpu_usage}%</span>
                      <span style={{ fontSize: "11px", color: "#64748b" }}>MEM: {server.memory_usage}%</span>
                      <span style={{ fontSize: "11px", color: "#64748b" }}>DISK: {server.disk_usage}%</span>
                    </div>
                  </div>
                </div>
                {server.insights?.map((insight, i) => (
                  <div key={i} style={{ marginTop: "6px", color: "#f59e0b", fontSize: "13px" }}>• {insight}</div>
                ))}
              </div>
            ))
          )}
        </div>
      </main>
    </div>
  );
}