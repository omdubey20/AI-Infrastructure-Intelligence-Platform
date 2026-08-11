import React from "react";

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#0f172a",
          color: "#f8fafc",
          fontFamily: "'Inter', sans-serif",
        }}>
          <div style={{
            textAlign: "center",
            padding: "48px",
            background: "rgba(239, 68, 68, 0.08)",
            borderRadius: "16px",
            border: "1px solid rgba(239, 68, 68, 0.2)",
            maxWidth: "480px",
          }}>
            <div style={{ fontSize: "48px", marginBottom: "16px" }}>⚠️</div>
            <h1 style={{ fontSize: "24px", fontWeight: 700, marginBottom: "12px", color: "#ef4444" }}>
              Something went wrong
            </h1>
            <p style={{ color: "#94a3b8", marginBottom: "24px", lineHeight: 1.6 }}>
              An unexpected error occurred. Please try refreshing the page.
            </p>
            <button
              onClick={() => window.location.reload()}
              style={{
                padding: "10px 24px",
                background: "linear-gradient(135deg, #3b82f6, #6366f1)",
                color: "#fff",
                border: "none",
                borderRadius: "8px",
                cursor: "pointer",
                fontSize: "14px",
                fontWeight: 600,
              }}
            >
              Reload Page
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
