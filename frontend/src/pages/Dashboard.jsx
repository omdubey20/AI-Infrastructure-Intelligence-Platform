import React, { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { useNavigate } from "react-router-dom";
import api from "../api/axios";

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
    api.get("/stats/dashboard")
      .then((res) => setStats(res.data))
      .catch((err) => console.error(err));
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
    } catch (err) {
      setScanResult({ success: false, message: "Scan failed. Check backend logs." });
    } finally {
      setScanning(false);
    }
  };

  const handleLogout = () => { logout(); navigate("/login"); };

  const cards = [
    { label: "Total Servers", value: stats.total_servers, icon: "🖥️", color: "#3b82f6" },
    { label: "Projects", value: stats.total_projects, icon: "📁", color: "#10b981" },
    { label: "Healthy", value: stats.healthy_servers, icon: "✅", color: "#22c55e" },
    { label: "Warnings", value: stats.warning_servers, icon: "⚠️", color: "#f59e0b" },
    { label: "Critical", value: stats.critical_servers, icon: "🚨", color: "#ef4444" }
  ];

  const navItems = [
    { path: "/", icon: "📊", label: "Dashboard" },
    { path: "/servers", icon: "🖥️", label: "Servers" },
    { path: "/projects", icon: "📁", label: "Projects" },
    { path: "/cleanup", icon: "🧹", label: "Cleanup" }
  ];

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "#0f172a" }}>
      <aside style={{ width: "250px", background: "#1e293b", padding: "24px 16px", borderRight: "1px solid #334155" }}>
        <h2 style={{ color: "white", marginBottom: "32px", fontSize: "16px", fontWeight: "bold" }}>ServerManager Pro</h2>
        {navItems.map((item) => (
          <div key={item.path} onClick={() => navigate(item.path)}
            style={{ padding: "12px", marginBottom: "8px", borderRadius: "8px", cursor: "pointer",
              color: window.location.pathname === item.path ? "white" : "#94a3b8",
              background: window.location.pathname === item.path ? "#2563eb" : "transparent" }}>
            {item.icon} {item.label}
          </div>
        ))}
        <div onClick={handleLogout} style={{ marginTop: "40px", color: "#ef4444", cursor: "pointer", padding: "12px" }}>
          🚪 Logout
        </div>
      </aside>

      <main style={{ flex: 1, padding: "32px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "8px" }}>
          <div>
            <h1 style={{ color: "white", marginBottom: "4px" }}>Infrastructure Dashboard</h1>
            <p style={{ color: "#94a3b8", margin: 0 }}>Real-time server health and risk monitoring</p>
          </div>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "8px" }}>
            <button onClick={handleScan} disabled={scanning}
              style={{ background: scanning ? "#1e3a5f" : "#2563eb", color: "white", border: "none",
                padding: "12px 24px", borderRadius: "8px", cursor: scanning ? "not-allowed" : "pointer",
                fontWeight: "600", fontSize: "14px", display: "flex", alignItems: "center", gap: "8px" }}>
              {scanning ? (
                <>
                  <span style={{ display: "inline-block", width: "14px", height: "14px", border: "2px solid white",
                    borderTopColor: "transparent", borderRadius: "50%",
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
          <div style={{ padding: "12px 16px", borderRadius: "8px", marginBottom: "24px", marginTop: "16px",
            background: scanResult.success ? "#052e16" : "#2d0a0a",
            border: `1px solid ${scanResult.success ? "#16a34a" : "#dc2626"}`,
            color: scanResult.success ? "#4ade80" : "#f87171", fontSize: "14px" }}>
            {scanResult.success ? "✅" : "❌"} {scanResult.message}
          </div>
        )}

        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(180px,1fr))", gap: "20px", marginBottom: "30px", marginTop: "24px" }}>
          {cards.map((card) => (
            <div key={card.label} style={{ background: "#1e293b", padding: "24px", borderRadius: "12px", border: "1px solid #334155" }}>
              <div style={{ fontSize: "28px", marginBottom: "10px" }}>{card.icon}</div>
              <div style={{ color: "#94a3b8", fontSize: "14px" }}>{card.label}</div>
              <div style={{ color: card.color, fontSize: "34px", fontWeight: "bold" }}>{card.value}</div>
            </div>
          ))}
        </div>

        <div style={{ background: "#1e293b", padding: "24px", borderRadius: "12px", border: "1px solid #334155" }}>
          <h2 style={{ color: "white", marginBottom: "20px" }}>🚨 Top Risk Servers</h2>
          {stats.top_risk_servers.length === 0 ? (
            <p style={{ color: "#94a3b8" }}>No servers found. Click Scan All Servers to discover.</p>
          ) : (
            stats.top_risk_servers.map((server) => (
              <div key={server.id} style={{ padding: "18px", marginBottom: "12px", borderRadius: "10px",
                background: "#0f172a", border: "1px solid #334155" }}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <div>
                    <div style={{ color: "white", fontWeight: "bold", fontSize: "16px" }}>{server.name}</div>
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
                {server.insights?.map((insight, index) => (
                  <div key={index} style={{ marginTop: "8px", color: "#f59e0b", fontSize: "13px" }}>• {insight}</div>
                ))}
              </div>
            ))
          )}
        </div>
      </main>
    </div>
  );
}