import React, { createContext, useContext, useState } from "react";

const AuthContext = createContext(null);

function getTokenRole(token) {
  if (!token) return "viewer";
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return payload.role || "viewer";
  } catch (e) {
    return "viewer";
  }
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem("token"));
  const [role, setRole] = useState(() => getTokenRole(localStorage.getItem("token")));

  const login = (t) => {
    localStorage.setItem("token", t);
    setToken(t);
    setRole(getTokenRole(t));
  };

  const logout = () => {
    localStorage.removeItem("token");
    setToken(null);
    setRole("viewer");
  };

  return (
    <AuthContext.Provider value={{ token, role, login, logout, user: null, loadingUser: false }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) return { token: null, role: "viewer", login: () => {}, logout: () => {}, user: null };
  return context;
}
