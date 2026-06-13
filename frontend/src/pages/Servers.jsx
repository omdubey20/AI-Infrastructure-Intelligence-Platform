import React, { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import api from '../api/axios';
import { useAuth } from '../context/AuthContext';

const NAV = [
  { path: '/', label: 'Dashboard' },
  { path: '/servers', label: 'Servers' },
  { path: '/projects', label: 'Projects' },
  { path: '/cleanup', label: 'Cleanup' },
];

const initialForm = {
  name: '',
  ip_address: '',
  environment: 'production',
  status: 'active',
  description: '',
};

export default function Servers() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [servers, setServers] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [editServer, setEditServer] = useState(null);
  const [form, setForm] = useState(initialForm);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);

  const fetchServers = async () => {
    setFetching(true);
    setError('');
    try {
      const res = await api.get('/servers/');
      setServers(Array.isArray(res.data) ? res.data : []);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load servers.');
    } finally {
      setFetching(false);
    }
  };

  useEffect(() => {
    fetchServers();
  }, []);

  const openAddForm = () => {
    setEditServer(null);
    setForm(initialForm);
    setError('');
    setShowForm(true);
  };

  const openEditForm = (server) => {
    setEditServer(server);
    setForm({
      name: server.name || '',
      ip_address: server.ip_address || '',
      environment: server.environment || 'production',
      status: server.status || 'active',
      description: server.description || '',
    });
    setError('');
    setShowForm(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      if (editServer) {
        await api.put(`/servers/${editServer.id}`, form);
      } else {
        await api.post('/servers/', form);
      }

      await fetchServers();
      setShowForm(false);
      setEditServer(null);
      setForm(initialForm);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save server.');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    const ok = window.confirm('Delete this server?');
    if (!ok) return;

    try {
      await api.delete(`/servers/${id}`);
      await fetchServers();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete server.');
    }
  };

  const inputStyle = {
    width: '100%',
    padding: '10px 12px',
    background: '#0f172a',
    border: '1px solid #334155',
    borderRadius: '8px',
    color: 'white',
    fontSize: '14px',
    boxSizing: 'border-box',
  };

  const labelStyle = {
    display: 'block',
    color: '#94a3b8',
    fontSize: '14px',
    marginBottom: '6px',
  };

  const buttonStyle = {
    border: 'none',
    padding: '10px 16px',
    borderRadius: '8px',
    cursor: 'pointer',
    fontWeight: '600',
  };

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: '#0f172a' }}>
      <aside
        style={{
          width: '240px',
          background: '#1e293b',
          padding: '24px 16px',
          borderRight: '1px solid #334155',
        }}
      >
        <h2 style={{ color: 'white', fontSize: '18px', fontWeight: 'bold', marginBottom: '32px' }}>
          ServerManager Pro
        </h2>

        {NAV.map((item) => {
          const active = location.pathname === item.path;
          return (
            <div
              key={item.path}
              onClick={() => navigate(item.path)}
              style={{
                padding: '10px 16px',
                borderRadius: '8px',
                color: active ? 'white' : '#94a3b8',
                background: active ? '#2563eb' : 'transparent',
                cursor: 'pointer',
                marginBottom: '4px',
              }}
            >
              {item.label}
            </div>
          );
        })}

        <div
          onClick={() => {
            logout();
            navigate('/login');
          }}
          style={{ padding: '10px 16px', color: '#ef4444', cursor: 'pointer', marginTop: '32px' }}
        >
          Logout
        </div>
      </aside>

      <main style={{ flex: 1, padding: '32px' }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '24px',
          }}
        >
          <div>
            <h1 style={{ color: 'white', fontSize: '28px', fontWeight: 'bold', marginBottom: '4px' }}>
              Servers
            </h1>
            <p style={{ color: '#94a3b8' }}>
              {servers.length} server{servers.length !== 1 ? 's' : ''} registered
            </p>
          </div>

          <button
            onClick={openAddForm}
            style={{
              ...buttonStyle,
              background: '#2563eb',
              color: 'white',
            }}
          >
            + Add Server
          </button>
        </div>

        {error && (
          <div
            style={{
              background: '#ef444420',
              border: '1px solid #ef4444',
              color: '#ef4444',
              padding: '10px',
              borderRadius: '8px',
              marginBottom: '16px',
              fontSize: '14px',
            }}
          >
            {error}
          </div>
        )}

        {showForm && (
          <div
            style={{
              background: '#1e293b',
              borderRadius: '12px',
              padding: '24px',
              border: '1px solid #334155',
              marginBottom: '24px',
            }}
          >
            <h3 style={{ color: 'white', marginBottom: '16px' }}>
              {editServer ? 'Edit Server' : 'Add New Server'}
            </h3>

            <form onSubmit={handleSubmit}>
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr',
                  gap: '16px',
                  marginBottom: '16px',
                }}
              >
                <div>
                  <label style={labelStyle}>Server Name</label>
                  <input
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    required
                    placeholder="e.g. Web Server 01"
                    style={inputStyle}
                  />
                </div>

                <div>
                  <label style={labelStyle}>IP Address</label>
                  <input
                    value={form.ip_address}
                    onChange={(e) => setForm({ ...form, ip_address: e.target.value })}
                    required
                    placeholder="e.g. 192.168.1.1"
                    style={inputStyle}
                  />
                </div>

                <div>
                  <label style={labelStyle}>Environment</label>
                  <input
                    value={form.environment}
                    onChange={(e) => setForm({ ...form, environment: e.target.value })}
                    placeholder="production / staging / dev"
                    style={inputStyle}
                  />
                </div>

                <div>
                  <label style={labelStyle}>Status</label>
                  <input
                    value={form.status}
                    onChange={(e) => setForm({ ...form, status: e.target.value })}
                    placeholder="active / warning / offline"
                    style={inputStyle}
                  />
                </div>
              </div>

              <div style={{ marginBottom: '16px' }}>
                <label style={labelStyle}>Description</label>
                <input
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  placeholder="Short description"
                  style={inputStyle}
                />
              </div>

              <div style={{ display: 'flex', gap: '12px' }}>
                <button
                  type="submit"
                  disabled={loading}
                  style={{
                    ...buttonStyle,
                    background: '#2563eb',
                    color: 'white',
                  }}
                >
                  {loading ? 'Saving...' : editServer ? 'Update Server' : 'Add Server'}
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setShowForm(false);
                    setEditServer(null);
                    setError('');
                    setForm(initialForm);
                  }}
                  style={{
                    ...buttonStyle,
                    background: '#334155',
                    color: 'white',
                  }}
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        {fetching ? (
          <div
            style={{
              background: '#1e293b',
              borderRadius: '12px',
              padding: '32px',
              border: '1px solid #334155',
              color: '#94a3b8',
            }}
          >
            Loading servers...
          </div>
        ) : servers.length === 0 ? (
          <div
            style={{
              background: '#1e293b',
              borderRadius: '12px',
              padding: '48px',
              border: '1px solid #334155',
              textAlign: 'center',
            }}
          >
            <p style={{ color: '#94a3b8', fontSize: '16px' }}>
              No servers yet. Click + Add Server to get started.
            </p>
          </div>
        ) : (
          <div style={{ display: 'grid', gap: '12px' }}>
            {servers.map((s) => (
              <div
                key={s.id}
                style={{
                  background: '#1e293b',
                  borderRadius: '12px',
                  padding: '20px 24px',
                  border: '1px solid #334155',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <div>
                  <h3 style={{ color: 'white', fontWeight: '600', margin: '0 0 6px 0' }}>
                    {s.name}
                  </h3>

                  <p style={{ color: '#94a3b8', fontSize: '14px', margin: 0 }}>
                    {s.ip_address}
                    {s.environment ? ` • ${s.environment}` : ''}
                    {s.status ? ` • ${s.status}` : ''}
                  </p>

                  {s.description && (
                    <p style={{ color: '#64748b', fontSize: '13px', margin: '6px 0 0 0' }}>
                      {s.description}
                    </p>
                  )}
                </div>

                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    onClick={() => openEditForm(s)}
                    style={{
                      ...buttonStyle,
                      background: '#334155',
                      color: 'white',
                    }}
                  >
                    Edit
                  </button>

                  <button
                    onClick={() => handleDelete(s.id)}
                    style={{
                      ...buttonStyle,
                      background: '#ef444420',
                      color: '#ef4444',
                      border: '1px solid #ef4444',
                    }}
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}