import React, { useEffect, useState } from "react";
import api from "../api/axios";
import AIInsightCard from "../components/AIInsightCard";

export default function Intelligence() {
  const [mlStatus, setMlStatus] = useState(null);
  const [featureImportance, setFeatureImportance] = useState([]);
  const [insights, setInsights] = useState([]);
  const [predictions, setPredictions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [retraining, setRetraining] = useState(false);
  const [retrainMsg, setRetrainMsg] = useState(null);

  const loadIntel = async () => {
    try {
      const statusRes = await api.get("/ml/status");
      setMlStatus(statusRes.data);
    } catch (e) {
      console.error("ml/status error:", e);
    }

    try {
      const fiRes = await api.get("/ml/feature-importance");
      setFeatureImportance(fiRes.data?.features || []);
    } catch (e) {
      // feature importance might not be available
    }

    try {
      const insightsRes = await api.get("/ai/insights");
      setInsights(Array.isArray(insightsRes.data) ? insightsRes.data : []);
    } catch (e) {
      console.error("ai/insights error:", e);
    }

    try {
      const predRes = await api.get("/ml/predictions");
      setPredictions(Array.isArray(predRes.data) ? predRes.data : []);
    } catch (e) {
      console.error("ml/predictions error:", e);
    }

    setLoading(false);
  };

  useEffect(() => {
    loadIntel();
    const interval = setInterval(loadIntel, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleRetrain = async () => {
    setRetraining(true);
    setRetrainMsg(null);
    try {
      const res = await api.post("/ml/train");
      setRetrainMsg(`✅ MLflow Model Retrained! Run ID: ${res.data.run_id?.slice(0, 8)}... (R²: ${res.data.metrics?.r2_score})`);
      loadIntel();
    } catch (e) {
      setRetrainMsg("❌ Retraining failed.");
    } finally {
      setRetraining(false);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: "32px", background: "#080e1a", minHeight: "100vh", color: "#94a3b8" }}>
        Loading intelligence data...
      </div>
    );
  }

  return (
    <div style={{ padding: "32px", background: "#080e1a", minHeight: "100vh" }}>
      <div style={{ marginBottom: "28px", display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <p style={{ fontSize: "11px", color: "#8b5cf6", fontWeight: 800, letterSpacing: "0.14em", marginBottom: "6px" }}>
            MACHINE LEARNING & AI ENGINE
          </p>
          <h1 style={{ fontSize: "24px", fontWeight: 800, color: "#f1f5f9" }}>Intelligence Platform</h1>
          <p style={{ fontSize: "13px", color: "#94a3b8", marginTop: "4px" }}>
            MLflow experiment tracking, SHAP feature importance, and automated AI risk recommendations
          </p>
        </div>

        <button onClick={handleRetrain} disabled={retraining} style={{
          padding: "12px 24px",
          background: "linear-gradient(135deg, #8b5cf6, #6366f1)",
          color: "white", border: "none", borderRadius: "10px", fontWeight: 800, cursor: "pointer"
        }}>
          {retraining ? <><span className="spinner" /> Retraining Model...</> : "⚡ Retrain MLflow Pipeline"}
        </button>
      </div>

      {retrainMsg && (
        <div style={{ padding: "12px 16px", borderRadius: "8px", background: "rgba(139,92,246,0.12)", border: "1px solid rgba(139,92,246,0.3)", color: "#c084fc", fontSize: "13px", fontWeight: 600, marginBottom: "24px" }}>
          {retrainMsg}
        </div>
      )}

      {/* Grid ML Specs & Feature Importance */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px", marginBottom: "28px" }}>
        {/* MLflow Model Specs */}
        <div className="card">
          <h3 style={{ fontSize: "13px", fontWeight: 800, color: "#c084fc", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "16px" }}>
            MLflow Registry & Experiment Tracking
          </h3>
          <div style={{ fontSize: "13px", color: "#94a3b8", display: "grid", gap: "10px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid #1d3047", paddingBottom: "8px" }}>
              <span>Experiment Name</span>
              <span style={{ fontWeight: 700, color: "#f1f5f9" }}>{mlStatus?.experiment_name || "Server_Risk_Scoring_Model"}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid #1d3047", paddingBottom: "8px" }}>
              <span>Algorithm</span>
              <span style={{ fontWeight: 700, color: "#38bdf8" }}>{mlStatus?.algorithm || "XGBoost Regressor"}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid #1d3047", paddingBottom: "8px" }}>
              <span>Model Status</span>
              <span className={mlStatus?.model_loaded ? "badge badge-green" : "badge badge-red"}>
                {mlStatus?.model_loaded ? "Model Loaded" : "No Model"}
              </span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid #1d3047", paddingBottom: "8px" }}>
              <span>MLflow Status</span>
              <span className="badge badge-purple">{mlStatus?.mlflow_status || "Active"}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span>Explainability</span>
              <span style={{ fontWeight: 700, color: "#4ade80" }}>SHAP Value Analysis</span>
            </div>
          </div>
        </div>

        {/* Feature Importance */}
        <div className="card">
          <h3 style={{ fontSize: "13px", fontWeight: 800, color: "#38bdf8", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "16px" }}>
            SHAP Feature Importance Weights
          </h3>
          {featureImportance.length === 0 ? (
            <p style={{ color: "#64748b", fontSize: "13px" }}>Click "Retrain MLflow Pipeline" to generate feature importance weights.</p>
          ) : (
            featureImportance.map((item) => (
              <div key={item.feature} style={{ marginBottom: "10px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", marginBottom: "4px" }}>
                  <span style={{ color: "#f1f5f9", fontWeight: 600 }}>{item.feature}</span>
                  <span style={{ color: "#38bdf8", fontWeight: 700 }}>{(item.importance * 100).toFixed(0)}%</span>
                </div>
                <div style={{ width: "100%", height: "6px", background: "#09111d", borderRadius: "999px" }}>
                  <div style={{ width: `${item.importance * 100}%`, height: "100%", background: "linear-gradient(90deg, #38bdf8, #8b5cf6)", borderRadius: "999px" }} />
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* ML Predictions Table */}
      {predictions.length > 0 && (
        <div className="card" style={{ padding: 0, marginBottom: "28px" }}>
          <div style={{ padding: "16px 24px", borderBottom: "1px solid #1d3047" }}>
            <h3 style={{ color: "#f1f5f9", fontSize: "14px", fontWeight: 800 }}>ML Risk Predictions ({predictions.length} servers)</h3>
          </div>
          <table>
            <thead>
              <tr>
                <th>Server</th>
                <th>Predicted Risk</th>
                <th>CPU %</th>
                <th>Memory %</th>
                <th>Disk %</th>
              </tr>
            </thead>
            <tbody>
              {predictions.map((p, i) => (
                <tr key={i}>
                  <td style={{ fontWeight: 700, color: "#f1f5f9" }}>{p.server_name}</td>
                  <td>
                    <span className={p.predicted_risk_score >= 60 ? "badge badge-red" : p.predicted_risk_score >= 40 ? "badge badge-amber" : "badge badge-green"}>
                      {p.predicted_risk_score}
                    </span>
                  </td>
                  <td style={{ color: "#94a3b8" }}>{p.cpu_usage || 0}%</td>
                  <td style={{ color: "#94a3b8" }}>{p.memory_usage || 0}%</td>
                  <td style={{ color: "#94a3b8" }}>{p.disk_usage || 0}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* AI Insights & Recommendations Feed */}
      <h3 style={{ fontSize: "16px", fontWeight: 800, color: "#f1f5f9", marginBottom: "16px" }}>
        Automated Infrastructure AI Insights ({insights.length})
      </h3>

      {insights.length === 0 ? (
        <div className="card" style={{ color: "#64748b" }}>No active AI alerts. All infrastructure operates within healthy parameters.</div>
      ) : (
        insights.map((ins) => (
          <AIInsightCard
            key={ins.id}
            title={ins.title}
            description={ins.description}
            recommendation={ins.recommendation}
            severity={ins.severity}
            category={ins.category}
          />
        ))
      )}
    </div>
  );
}
