import React, { createContext, useContext, useState, useEffect } from "react";
import api from "../api/axios";

const DataContext = createContext(null);

export function DataProvider({ children }) {
  const [stats, setStats] = useState(null);
  const [servers, setServers] = useState([]);
  const [projects, setProjects] = useState([]);
  const [duplicates, setDuplicates] = useState([]);
  const [cleanup, setCleanup] = useState(null);
  const [loaded, setLoaded] = useState(false);

  const preloadAll = async () => {
    if (loaded) return;
    try {
      const [s, sv, p, d, c] = await Promise.all([
        api.get("/stats/dashboard"),
        api.get("/servers/"),
        api.get("/projects/"),
        api.get("/projects/duplicates"),
        api.get("/cleanup/report"),
      ]);
      setStats(s.data);
      setServers(sv.data);
      setProjects(p.data);
      setDuplicates(d.data);
      setCleanup(c.data);
      setLoaded(true);
    } catch (e) {
      console.error("Preload failed:", e);
    }
  };

  const refresh = () => { setLoaded(false); };

  useEffect(() => {
    const interval = setInterval(() => {
      setLoaded(false);
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <DataContext.Provider value={{ stats, servers, projects, duplicates, cleanup, loaded, preloadAll, refresh }}>
      {children}
    </DataContext.Provider>
  );
}

export function useData() {
  const ctx = useContext(DataContext);
  if (!ctx) return { stats: null, servers: [], projects: [], duplicates: [], cleanup: null, loaded: false, preloadAll: () => {}, refresh: () => {} };
  return ctx;
}
