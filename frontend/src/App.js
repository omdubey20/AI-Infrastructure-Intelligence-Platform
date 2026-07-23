import React, { useEffect } from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Servers from "./pages/Servers";
import Projects from "./pages/Projects";
import Cleanup from "./pages/Cleanup";
import { DataProvider, useData } from "./context/DataContext";

function PrivateRoute({ children }) {
  const token = localStorage.getItem("token");
  return token ? children : <Navigate to="/login" />;
}

function Layout({ children }) {
  const { preloadAll, loaded } = useData();

  useEffect(() => {
    if (!loaded) preloadAll();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loaded]);

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
    <DataProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/dashboard" element={<PrivateRoute><Layout><Dashboard /></Layout></PrivateRoute>} />
          <Route path="/servers" element={<PrivateRoute><Layout><Servers /></Layout></PrivateRoute>} />
          <Route path="/projects" element={<PrivateRoute><Layout><Projects /></Layout></PrivateRoute>} />
          <Route path="/cleanup" element={<PrivateRoute><Layout><Cleanup /></Layout></PrivateRoute>} />
          <Route path="*" element={<Navigate to="/dashboard" />} />
        </Routes>
      </Router>
    </DataProvider>
  );
}
