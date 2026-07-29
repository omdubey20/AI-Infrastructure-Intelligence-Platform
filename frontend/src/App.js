import React from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
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
import { AuthProvider } from "./context/AuthContext";

function PrivateRoute({ children }) {
  const token = localStorage.getItem("token");
  return token ? children : <Navigate to="/login" />;
}

function Layout({ children }) {
  const isMobile = window.innerWidth <= 768;
  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "#0f172a" }}>
      <Sidebar />
      <main style={{ flex: 1, overflowY: "auto", background: "#0f172a", paddingTop: isMobile ? "56px" : "0" }}>
        {children}
      </main>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
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
    </AuthProvider>
  );
}
