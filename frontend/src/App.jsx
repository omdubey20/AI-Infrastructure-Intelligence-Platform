import React from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import ErrorBoundary from "./components/ErrorBoundary";

import Sidebar from "./components/Sidebar";

import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Servers from "./pages/Servers";
import ServerDetail from "./pages/ServerDetail";
import Projects from "./pages/Projects";
import Duplicates from "./pages/Duplicates";
import Inactive from "./pages/Inactive";
import Cleanup from "./pages/Cleanup";
import Intelligence from "./pages/Intelligence";

function PrivateRoute({ children }) {
  const token = localStorage.getItem("token");
  if (!token) return <Navigate to="/login" />;
  // Check if token is expired (JWT payload.exp)
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    if (payload.exp && payload.exp * 1000 < Date.now()) {
      localStorage.removeItem("token");
      return <Navigate to="/login" />;
    }
  } catch {
    localStorage.removeItem("token");
    return <Navigate to="/login" />;
  }
  return children;
}

function Layout({ children }) {
  return (
    <div style={{ display: "flex", minHeight: "100vh", width: "100%", background: "#080e1a" }}>
      <Sidebar />
      <main style={{ flex: 1, minHeight: "100vh", overflowY: "auto", background: "transparent" }}>
        {children}
      </main>
    </div>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <Router>
        <Routes>
          <Route path="/login" element={<Login />} />

          <Route path="/dashboard" element={<PrivateRoute><Layout><Dashboard /></Layout></PrivateRoute>} />
          <Route path="/servers" element={<PrivateRoute><Layout><Servers /></Layout></PrivateRoute>} />
          <Route path="/servers/:id" element={<PrivateRoute><Layout><ServerDetail /></Layout></PrivateRoute>} />
          <Route path="/projects" element={<PrivateRoute><Layout><Projects /></Layout></PrivateRoute>} />
          <Route path="/duplicates" element={<PrivateRoute><Layout><Duplicates /></Layout></PrivateRoute>} />
          <Route path="/inactive" element={<PrivateRoute><Layout><Inactive /></Layout></PrivateRoute>} />
          <Route path="/cleanup" element={<PrivateRoute><Layout><Cleanup /></Layout></PrivateRoute>} />
          <Route path="/intelligence" element={<PrivateRoute><Layout><Intelligence /></Layout></PrivateRoute>} />

          <Route path="*" element={<Navigate to="/dashboard" />} />
        </Routes>
      </Router>
    </ErrorBoundary>
  );
}