import React, { useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import api from "../api/axios";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login, token } = useAuth();

  if (token) return <Navigate to="/" replace />;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const p = new URLSearchParams();
      p.append("username", username);
      p.append("password", password);

      const res = await api.post("/auth/login", p, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });

      login(res.data.access_token);
    } catch (err) {
      setError(err?.response?.data?.detail || "Invalid username or password");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", background: "#0f172a", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ width: "400px", background: "#1e293b", borderRadius: "16px", padding: "32px", border: "1px solid #334155" }}>
        <h1 style={{ color: "white", textAlign: "center", marginBottom: "8px" }}>ServerManager Pro</h1>
        <p style={{ color: "#94a3b8", textAlign: "center", marginBottom: "24px" }}>Sign in to your account</p>
        {error && <p style={{ color: "#f87171", marginBottom: "16px" }}>{error}</p>}
        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: "16px" }}>
            <p style={{ color: "#cbd5e1", marginBottom: "6px" }}>Username</p>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              style={{ width: "100%", background: "#0f172a", border: "1px solid #475569", color: "white", padding: "10px", borderRadius: "8px", boxSizing: "border-box" }}
            />
          </div>
          <div style={{ marginBottom: "24px" }}>
            <p style={{ color: "#cbd5e1", marginBottom: "6px" }}>Password</p>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              style={{ width: "100%", background: "#0f172a", border: "1px solid #475569", color: "white", padding: "10px", borderRadius: "8px", boxSizing: "border-box" }}
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            style={{ width: "100%", background: "#2563eb", color: "white", border: "none", padding: "12px", borderRadius: "8px", fontSize: "16px", cursor: "pointer" }}
          >
            {loading ? "Signing in..." : "Sign In"}
          </button>
        </form>
      </div>
    </div>
  );
}