import React, { createContext, useContext, useState, useEffect } from "react";
import api from "../api/axios";

const DataContext = createContext(null);

export function DataProvider({ children }) {
  const [stats, setStats] = useState(null);
  const [servers, setServers] = useState([]);
  const [projects, setProjects] = useState([]);
  const [cleanup, setCleanup] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loaded, setLoaded] = useState(false);

  const preloadAll = async () => {
    if (loading || loaded) return;
    setLoading(true);
    try {
      const [statsRes, serversRes, projectsRes, cleanupRes] = await Promise.all([
        api.get("/stats/dashboard"),
        api.get("/servers/"),
        api.get("/projects/"),
        api.get("/cleanup/report"),
      ]);
      setStats(statsRes.data);
      setServers(serversRes.data);
      setProjects(projectsRes.data);
      setCleanup(cleanupRes.data);
      setLoaded(true);
    } catch (e) {
      console.error("Preload failed:", e);
    } finally {
      setLoading(false);
    }
  };

  const refresh = () => {
    setLoaded(false);
    preloadAll();
  };

  return (
    <DataContext.Provider value={{ stats, servers, projects, cleanup, loading, loaded, preloadAll, refresh }}>
      {children}
    </DataContext.Provider>
  );
}

export function useData() {
  return useContext(DataContext);
}
