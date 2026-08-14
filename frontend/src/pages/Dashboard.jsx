import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/axios";
import StatCard from "../components/StatCard";
import AIInsightCard from "../components/AIInsightCard";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend
} from "recharts";

const HEALTH_COLORS = { Healthy: "#22c55e", Warning: "#f59e0b", Critical: "#f87171" };

export default function Dashboard() {
  const navigate = useNavigate();
  const [scanning, setScanning] = useState(false);
  const [mlTraining, setMlTraining] = useState(false);
  const [bannerMsg, setBannerMsg] = useState(null);
  const [insights, setInsights] = useState([]);

  const [stats, setStats] = useState({
    total_servers: 0,
    total_projects: 0,
    live_projects: 0,
    duplicate_projects: 0,
    inactive_projects: 0,
    healthy_servers: 0,
    warning_servers: 0,
    critical_servers: 0,
    top_risk_servers: [],
  });

  const fetchStats = async () => {
    try {
      const sRes = await api.get("/stats/dashboard");
      if (sRes?.data) setStats(sRes.data);
    } catch (e) {
      console.error("Failed to fetch dashboard stats:", e);
    }

    try {
      const iRes = await api.get("/ai/insights");
      if (Array.isArray(iRes?.data)) setInsights(iRes.data.slice(0, 3));
    } catch (e) {
      console.error("Failed to fetch AI insights:", e);
    }
  };

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleScan = async () => {
    setScanning(true);
    setBannerMsg(null);
    try {
      const res = await api.post("/discovery/scan");
      setBannerMsg({ ok: true, msg: `SSH/WHM discovery scan completed for ${res.data.servers_scanned || 0} server(s).` });
      fetchStats();
    } catch (e) {
      setBannerMsg({ ok: false, msg: "Discovery scan failed." });
    } finally {
      setScanning(false);
    }
  };

  const handleRetrainML = async () => {
    setMlTraining(true);
    setBannerMsg(null);
    try {
      const res = await api.post("/ml/train");
      setBannerMsg({ ok: true, msg: `MLflow Pipeline Retrained! Run ID: ${res.data.run_id?.slice(0, 8)} (R²: ${res.data.metrics?.r2_score})` });
      fetchStats();
    } catch (e) {
      setBannerMsg({ ok: false, msg: "ML training failed." });
    } finally {
      setMlTraining(false);
    }
  };

  const barData = useMemo(
    () =>
      (stats.top_risk_servers || []).map((s) => ({
        name: s.name?.length > 12 ? s.name.slice(0, 12) + "..." : s.name,
        CPU: s.cpu_usage || 0,
        Memory: s.memory_usage || 0,
        Disk: s.disk_usage || 0,
      })),
    [stats.top_risk_servers]
  );

  const pieData = useMemo(
    () =>
      [
        { name: "Healthy", value: stats.healthy_servers || 0 },
        { name: "Warning", value: stats.warning_servers || 0 },
        { name: "Critical", value: stats.critical_servers || 0 },
      ].filter((d) => d.value > 0),
    [stats]
  );

  return (
    <div style={{ padding: "32px", background: "#080e1a", minHeight: "100vh" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "28px", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <p style={{ fontSize: "11px", color: "#38bdf8", fontWeight: 800, letterSpacing: "0.14em", marginBottom: "6px" }}>
            INFRASTRUCTURE INTELLIGENCE DASHBOARD
          </p>
          <h1 style={{ fontSize: "24px", fontWeight: 800, color: "#f1f5f9" }}>System Overview</h1>
          <p style={{ fontSize: "13px", color: "#94a3b8", marginTop: "4px" }}>
            Centralized server management, live project discovery, duplicate detection, and ML risk predictions
          </p>
        </div>

        <div style={{ display: "flex", gap: "10px" }}>
          <button onClick={handleScan} disabled={scanning} className="btn-primary">
            {scanning ? <><span className="spinner" /> Scanning...</> : "🔍 Scan Infrastructure"}
          </button>
          <button onClick={handleRetrainML} disabled={mlTraining} style={{
            padding: "10px 18px", background: "linear-gradient(135deg,#8b5cf6,#6366f1)",
            color: "white", border: "none", borderRadius: "10px", fontWeight: 800, cursor: "pointer"
          }}>
            {mlTraining ? <><span className="spinner" /> Retraining...</> : "⚡ Retrain MLflow"}
          </button>
        </div>
      </div>

      {bannerMsg && (
        <div style={{ padding: "12px 16px", borderRadius: "8px", background: bannerMsg.ok ? "rgba(34,197,94,0.12)" : "rgba(248,113,113,0.12)", border: bannerMsg.ok ? "1px solid rgba(34,197,94,0.3)" : "1px solid rgba(248,113,113,0.3)", color: bannerMsg.ok ? "#4ade80" : "#f87171", fontSize: "13px", fontWeight: 600, marginBottom: "24px" }}>
          {bannerMsg.msg}
        </div>
      )}

      {/* KPI Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: "16px", marginBottom: "28px" }}>
        <div onClick={() => navigate("/servers")} style={{ cursor: "pointer" }}>
          <StatCard title="Total Servers" value={stats.total_servers} icon="🖥️" color="blue" subtitle="Live SSH / WHM" />
        </div>
        <div onClick={() => navigate("/projects")} style={{ cursor: "pointer" }}>
          <StatCard title="Live Projects" value={stats.live_projects || stats.total_projects} icon="📁" color="teal" subtitle="Active deployments" />
        </div>
        <div onClick={() => navigate("/monitoring")} style={{ cursor: "pointer" }}>
          <StatCard title="Website Uptime" value="24/7" icon="📈" color="green" subtitle="Live Latency & SSL" />
        </div>
        <div onClick={() => navigate("/security")} style={{ cursor: "pointer" }}>
          <StatCard title="Security & Alerts" value="Active" icon="🛡️" color="red" subtitle="Teams & Email Alerts" />
        </div>
        <div onClick={() => navigate("/duplicates")} style={{ cursor: "pointer" }}>
          <StatCard title="Duplicate Copies" value={stats.duplicate_projects} icon="👯" color="amber" subtitle="Cross-server clones" />
        </div>
      </div>

      {/* Charts */}
      {stats.top_risk_servers.length > 0 && (
        <div className="dashboard-grid-charts" style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "20px", marginBottom: "28px" }}>

          <div className="card">
            <h3 style={{ fontSize: "12px", fontWeight: 800, color: "#94a3b8", letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: "16px" }}>
              Server Resource Utilization (%)
            </h3>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={barData} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
                <XAxis dataKey="name" tick={{ fill: "#64748b", fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: "#64748b", fontSize: 11 }} domain={[0, 100]} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ background: "#0d1524", border: "1px solid #1d3047", borderRadius: "8px", color: "#f1f5f9" }} />
                <Legend wrapperStyle={{ color: "#64748b", fontSize: 11 }} />
                <Bar dataKey="CPU" fill="#38BDF8" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Memory" fill="#2DD4BF" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Disk" fill="#F59E0B" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="card">
            <h3 style={{ fontSize: "12px", fontWeight: 800, color: "#94a3b8", letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: "16px" }}>
              Fleet Health Status
            </h3>
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" innerRadius={55} outerRadius={80} paddingAngle={4} dataKey="value">
                  {pieData.map((entry, i) => (
                    <Cell key={i} fill={HEALTH_COLORS[entry.name]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ background: "#0d1524", border: "1px solid #1d3047", borderRadius: "8px", color: "#f1f5f9" }} />
                <Legend wrapperStyle={{ color: "#64748b", fontSize: 11 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* AI Alerts Feed */}
      {insights.length > 0 && (
        <div>
          <h3 style={{ fontSize: "14px", fontWeight: 800, color: "#f1f5f9", marginBottom: "14px" }}>
            Top AI Recommendations & Security Alerts
          </h3>
          {insights.map((ins) => (
            <AIInsightCard
              key={ins.id}
              title={ins.title}
              description={ins.description}
              recommendation={ins.recommendation}
              severity={ins.severity}
              category={ins.category}
            />
          ))}
        </div>
      )}
    </div>
  );
}