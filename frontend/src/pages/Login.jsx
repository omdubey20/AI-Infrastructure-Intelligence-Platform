import React, { useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import api from "../api/axios";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError]       = useState("");
  const [loading, setLoading]   = useState(false);
  const { login, token }        = useAuth();

  if (token) return <Navigate to="/dashboard" replace />;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      const p = new URLSearchParams();
      p.append("username", username);
      p.append("password", password);
      const res = await api.post("/auth/login", p, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });
      login(res.data.access_token);
      window.location.href = "/dashboard";
    } catch (err) {
      setError(err?.response?.data?.detail || "Invalid username or password");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: "100vh", background: "#080e1a",
      display: "flex", alignItems: "center", justifyContent: "center",
      padding: "24px",
    }}>
      <div style={{
        position: "fixed", top: "20%", left: "50%", transform: "translateX(-50%)",
        width: "600px", height: "300px", borderRadius: "50%",
        background: "radial-gradient(ellipse, rgba(56,189,248,0.06) 0%, transparent 70%)",
        pointerEvents: "none",
      }} />

      <div className="animate-fadein" style={{
        width: "100%", maxWidth: "420px", margin: "0 auto",
        background: "#111c2e",
        border: "1px solid #2b4565",
        borderRadius: "16px", padding: "40px 36px",
      }}>
        <div style={{ textAlign: "center", marginBottom: "32px" }}>
          <div style={{
            width: "48px", height: "48px", borderRadius: "12px",
            background: "linear-gradient(135deg, var(--accent-dim), var(--accent-2))",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: "24px", fontWeight: 800, color: "white",
            margin: "0 auto 14px",
            boxShadow: "0 0 24px rgba(56,189,248,0.3)",
            animation: "pulse-ring 2.4s ease-out infinite",
          }}>I</div>
          <h1 style={{ fontSize: "20px", fontWeight: 800, color: "#f1f5f9", marginBottom: "6px" }}>
            Infra Intel
          </h1>
          <p style={{ fontSize: "13px", color: "#94a3b8" }}>
            Server Manager Platform
          </p>
        </div>

        {error && (
          <div style={{
            background: "rgba(248,113,113,0.08)", border: "1px solid rgba(248,113,113,0.25)",
            borderRadius: "8px", padding: "10px 14px", marginBottom: "20px",
            color: "var(--red)", fontSize: "13px", display: "flex", alignItems: "center", gap: "8px",
          }}>
            ⚠ {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: "16px" }}>
            <label style={{ display: "block", fontSize: "12px", fontWeight: 600,
              color: "#64748b", marginBottom: "6px", letterSpacing: "0.05em" }}>
              USERNAME
            </label>
            <input
              className="input-base" style={{ width: "100%" }}
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              placeholder="Enter username"
              required
              autoFocus
            />
          </div>

          <div style={{ marginBottom: "28px" }}>
            <label style={{ display: "block", fontSize: "12px", fontWeight: 600,
              color: "#64748b", marginBottom: "6px", letterSpacing: "0.05em" }}>
              PASSWORD
            </label>
            <input
              className="input-base" style={{ width: "100%" }}
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="Enter password"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="btn-primary"
            style={{ width: "100%", justifyContent: "center", padding: "12px", fontSize: "14px" }}
          >
            {loading ? (
              <><span className="spinner" /> Signing in...</>
            ) : "Sign In →"}
          </button>
        </form>

        <p style={{ textAlign: "center", marginTop: "24px",
          fontSize: "11px", color: "#64748b", letterSpacing: "0.05em" }}>
          Infra Intel v1.0 · Secure Access
        </p>
      </div>
    </div>
  );
}
