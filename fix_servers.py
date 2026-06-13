import os

base_back = "/Users/liluzi/Desktop/python/server-management-system/backend"
base_front = "/Users/liluzi/Desktop/python/server-management-system/frontend/src"

# main.py
open(base_back + "/main.py", "w").write("""from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
import models
from routers import servers
from auth import router as auth_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Server Management System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(servers.router)

@app.get("/")
def root():
    return {"message": "Server Management API"}
""")
print("main.py done")

# Servers.jsx
open(base_front + "/pages/Servers.jsx", "w").write("""import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/axios';
import { useAuth } from '../context/AuthContext';

const NAV = ["/", "/servers", "/projects", "/cleanup"];
const NAV_LABELS = ["Dashboard", "Servers", "Projects", "Cleanup"];
const NAV_ICONS = ["\\u{1F4CA}", "\\u{1F5A5}\\uFE0F", "\\u{1F4C1}", "\\u{1F9F9}"];

export default function Servers() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [servers, setServers] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [editServer, setEditServer] = useState(null);
  const [form, setForm] = useState({ name: '', ip_address: '', environment: 'production', status: 'active', description: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const fetchServers = () => {
    api.get('/servers/').then(res => setServers(res.data)).catch(() => {});
  };

  useEffect(() => { fetchServers(); }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      if (editServer) {
        await api.put('/servers/' + editServer.id, form);
      } else {
        await api.post('/servers/', form);
      }
      fetchServers();
      setShowForm(false);
      setEditServer(null);
      setForm({ name: '', ip_address: '', environment: 'production', status: 'active', description: '' });
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save server.');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this server?')) return;
    await api.delete('/servers/' + id);
    fetchServers();
  };

  const handleEdit = (s) => {
    setEditServer(s);
    setForm({ name: s.name, ip_address: s.ip_address, environment: s.environment, status: s.status, description: s.description || '' });
    setShowForm(true);
  };

  const envColor = (e) => e === 'production' ? '#ef4444' : e === 'staging' ? '#f59e0b' : '#10b981';
  const statusColor = (s) => s === 'active' ? '#10b981' : s === 'maintenance' ? '#f59e0b' : '#ef4444';

  const field = (key, label, placeholder, required=true) => (
    React.createElement('div', { key },
      React.createElement('label', { style: { display: 'block', color: '#94a3b8', fontSize: '14px', marginBottom: '6px' } }, label),
      React.createElement('input', {
        value: form[key],
        onChange: e => setForm({ ...form, [key]: e.target.value }),
        required,
        placeholder,
        style: { width: '100%', padding: '8px 12px', background: '#0f172a', border: '1px solid #334155', borderRadius: '6px', color: 'white', fontSize: '14px', boxSizing: 'border-box' }
      })
    )
  );

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: '#0f172a' }}>
      <aside style={{ width: '240px', background: '#1e293b', padding: '24px 16px', borderRight: '1px solid #334155' }}>
        <h2 style={{ color: 'white', fontSize: '18px', fontWeight: 'bold', marginBottom: '32px' }}>ServerManager Pro</h2>
        {NAV.map((path, i) => (
          <div key={path} onClick={() => navigate(path)} style={{ padding: '10px 16px', borderRadius: '8px', color: window.location.pathname === path ? 'white' : '#94a3b8', background: window.location.pathname === path ? '#2563eb' : 'transparent', cursor: 'pointer', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span>{NAV_ICONS[i]}</span><span>{NAV_LABELS[i]}</span>
          </div>
        ))}
        <div onClick={() => { logout(); navigate('/login'); }} style={{ padding: '10px 16px', borderRadius: '8px', color: '#ef4444', cursor: 'pointer', marginTop: '32px', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span>logout</span>
        </div>
      </aside>

      <main style={{ flex: 1, padding: '32px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
          <div>
            <h1 style={{ color: 'white', fontSize: '28px', fontWeight: 'bold', marginBottom: '4px' }}>Servers</h1>
            <p style={{ color: '#94a3b8' }}>{servers.length} server{servers.length !== 1 ? 's' : ''} registered</p>
          </div>
          <button onClick={() => { setShowForm(true); setEditServer(null); setForm({ name: '', ip_address: '', environment: 'production', status: 'active', description: '' }); }}
            style={{ background: '#2563eb', color: 'white', border: 'none', padding: '10px 20px', borderRadius: '8px', cursor: 'pointer', fontWeight: '600' }}>
            + Add Server
          </button>
        </div>

        {showForm && (
          <div style={{ background: '#1e293b', borderRadius: '12px', padding: '24px', border: '1px solid #334155', marginBottom: '24px' }}>
            <h3 style={{ color: 'white', marginBottom: '16px' }}>{editServer ? 'Edit Server' : 'Add New Server'}</h3>
            {error && <div style={{ background: '#ef444420', border: '1px solid #ef4444', color: '#ef4444', padding: '10px', borderRadius: '6px', marginBottom: '12px', fontSize: '14px' }}>{error}</div>}
            <form onSubmit={handleSubmit}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
                {field('name', 'Server Name', 'e.g. Web Server 01')}
                {field('ip_address', 'IP Address', 'e.g. 192.168.1.1')}
                <div>
                  abel style={{ display: 'block', color: '#94a3b8', fontSize: '14px', marginBottom: '6px' }}>Environment</label>
                  <select value={form.environment} onChange={e => setForm({ ...form, environment: e.target.value })}
                    style={{ width: '100%', padding: '8px 12px', background: '#0f172a', border: '1px solid #334155', borderRadius: '6px', color: 'white', fontSize: '14px' }}>
                    <option value="production">Production</option>
                    <option value="staging">Staging</option>
                    <option value="development">Development</option>
                  </select>
                </div>
                <div>
                  abel style={{ display: 'block', color: '#94a3b8', fontSize: '14px', marginBottom: '6px' }}>Status</label>
                  <select value={form.status} onChange={e => setForm({ ...form, status: e.target.value })}
                    style={{ width: '100%', padding: '8px 12px', background: '#0f172a', border: '1px solid #334155', borderRadius: '6px', color: 'white', fontSize: '14px' }}>
                    <option value="active">Active</option>
                    <option value="maintenance">Maintenance</option>
                    <option value="inactive">Inactive</option>
                  </select>
                </div>
              </div>
              {field('description', 'Description (optional)', 'Brief description...', false)}
              <div style={{ display: 'flex', gap: '12px', marginTop: '16px' }}>
                <button type="submit" disabled={loading}
                  style={{ background: '#2563eb', color: 'white', border: 'none', padding: '10px 24px', borderRadius: '8px', cursor: 'pointer', fontWeight: '600' }}>
                  {loading ? 'Saving...' : editServer ? 'Update Server' : 'Add Server'}
                </button>
                <button type="button" onClick={() => { setShowForm(false); setEditServer(null); setError(''); }}
                  style={{ background: '#334155', color: 'white', border: 'none', padding: '10px 24px', borderRadius: '8px', cursor: 'pointer' }}>
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        {servers.length === 0 ? (
          <div style={{ background: '#1e293b', borderRadius: '12px', padding: '48px', border: '1px solid #334155', textAlign: 'center' }}>
            <p style={{ color: '#94a3b8', fontSize: '16px' }}>No servers yet. Click + Add Server to get started.</p>
          </div>
        ) : (
          <div style={{ display: 'grid', gap: '12px' }}>
            {servers.map(s => (
              <div key={s.id} style={{ background: '#1e293b', borderRadius: '12px', padding: '20px 24px', border: '1px solid #334155', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '6px' }}>
                    <h3 style={{ color: 'white', fontWeight: '600', margin: 0 }}>{s.name}</h3>
                    <span style={{ background: statusColor(s.status) + '20', color: statusColor(s.status), padding: '2px 10px', borderRadius: '20px', fontSize: '12px', fontWeight: '600' }}>{s.status}</span>
                    <span style={{ background: envColor(s.environment) + '20', color: envColor(s.environment), padding: '2px 10px', borderRadius: '20px', fontSize: '12px', fontWeight: '600' }}>{s.environment}</span>
                  </div>
                  <p style={{ color: '#64748b', fontSize: '14px', margin: 0 }}>{s.ip_address}{s.description ? ' — ' + s.description : ''}</p>
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button onClick={() => handleEdit(s)} style={{ background: '#334155', color: 'white', border: 'none', padding: '8px 16px', borderRadius: '6px', cursor: 'pointer', fontSize: '14px' }}>Edit</button>
                  <button onClick={() => handleDelete(s.id)} style={{ background: '#ef444420', color: '#ef4444', border: '1px solid #ef4444', padding: '8px 16px', borderRadius: '6px', cursor: 'pointer', fontSize: '14px' }}>Delete</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
""")
print("Servers.jsx done")

print("\nALL DONE - now restart backend and check frontend")