import React, { useEffect, useState } from 'react';
import api from '../api/axios';


const FILTERS = ['all', 'live', 'unused', 'duplicates'];

export default function Projects() {
  const [projects, setProjects] = useState([]);
  const [filter, setFilter] = useState('all');
  const [loading, setLoading] = useState(true);

  const fetchProjects = async (f = 'all') => {
    setLoading(true);
    try {
      const endpoint = f === 'all' ? '/projects/' : `/projects/${f}`;
      const res = await api.get(endpoint);
      setProjects(Array.isArray(res.data) ? res.data : []);
    } catch (err) {
      console.error(err);
      setProjects([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchProjects(filter); }, [filter]);

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this project?')) return;
    await api.delete(`/projects/${id}`);
    fetchProjects(filter);
  };

  const riskColor = (score) =>
    score >= 70 ? '#ef4444' : score >= 40 ? '#f59e0b' : '#22c55e';

  return (
    <div style={{ padding: "32px" }}>

      <main style={{ flex: 1, padding: '32px' }}>
        <div style={{ marginBottom: '24px' }}>
          <h1 style={{ color: 'white', fontSize: '28px', fontWeight: 'bold', marginBottom: '4px' }}>
            Projects
          </h1>
          <p style={{ color: '#94a3b8' }}>
            {projects.length} project{projects.length !== 1 ? 's' : ''} found
          </p>
        </div>

        <div style={{ display: 'flex', gap: '8px', marginBottom: '24px' }}>
          {FILTERS.map(f => (
            <button key={f} onClick={() => setFilter(f)}
              style={{ padding: '8px 20px', borderRadius: '20px', border: 'none',
                cursor: 'pointer', fontWeight: '600', fontSize: '13px', textTransform: 'capitalize',
                background: filter === f ? '#2563eb' : '#1e293b',
                color: filter === f ? 'white' : '#94a3b8' }}>
              {f}
            </button>
          ))}
        </div>

        {loading ? (
          <div style={{ color: '#94a3b8', padding: '32px' }}>Loading projects...</div>
        ) : projects.length === 0 ? (
          <div style={{ background: '#1e293b', borderRadius: '12px', padding: '48px',
            border: '1px solid #334155', textAlign: 'center' }}>
            <p style={{ color: '#94a3b8', fontSize: '16px' }}>
              No projects found. Run a scan from the Dashboard first.
            </p>
          </div>
        ) : (
          <div style={{ background: '#1e293b', borderRadius: '12px', border: '1px solid #334155', overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: '#0f172a', borderBottom: '1px solid #334155' }}>
                  {['Project', 'Server', 'Path', 'Size', 'DNS', 'Web Config', 'Risk', ''].map(h => (
                    <th key={h} style={{ padding: '12px 16px', color: '#94a3b8', fontSize: '12px',
                      fontWeight: '600', textAlign: 'left', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {projects.map((p, i) => (
                  <tr key={p.id}
                    style={{ borderBottom: '1px solid #0f172a',
                      background: i % 2 === 0 ? '#1e293b' : '#162032' }}>
                    <td style={{ padding: '14px 16px', color: 'white', fontWeight: '600', fontSize: '14px' }}>
                      {p.project_name || p.name}
                    </td>
                    <td style={{ padding: '14px 16px', color: '#94a3b8', fontSize: '13px' }}>
                      {p.server_name || `Server ${p.server_id}`}
                    </td>
                    <td style={{ padding: '14px 16px', color: '#64748b', fontSize: '12px', fontFamily: 'monospace' }}>
                      {p.project_path || p.path || '-'}
                    </td>
                    <td style={{ padding: '14px 16px', color: '#94a3b8', fontSize: '13px' }}>
                      {p.size_mb ? `${p.size_mb} MB` : '-'}
                    </td>
                    <td style={{ padding: '14px 16px' }}>
                      <span style={{ padding: '3px 10px', borderRadius: '20px', fontSize: '11px', fontWeight: '600',
                        background: p.dns_points_here ? '#052e16' : '#2d0a0a',
                        color: p.dns_points_here ? '#4ade80' : '#f87171' }}>
                        {p.dns_points_here ? '● Live' : '● Dead'}
                      </span>
                    </td>
                    <td style={{ padding: '14px 16px' }}>
                      <span style={{ padding: '3px 10px', borderRadius: '20px', fontSize: '11px', fontWeight: '600',
                        background: p.web_config_active ? '#052e16' : '#2d0a0a',
                        color: p.web_config_active ? '#4ade80' : '#f87171' }}>
                        {p.web_config_active ? '● Active' : '● Inactive'}
                      </span>
                    </td>
                    <td style={{ padding: '14px 16px' }}>
                      <span style={{ fontWeight: 'bold', fontSize: '15px', color: riskColor(p.risk_score) }}>
                        {p.risk_score ?? '-'}
                      </span>
                    </td>
                    <td style={{ padding: '14px 16px' }}>
                      <button onClick={() => handleDelete(p.id)}
                        style={{ background: 'transparent', color: '#ef4444',
                          border: '1px solid #ef4444', padding: '5px 12px',
                          borderRadius: '6px', cursor: 'pointer', fontSize: '12px' }}>
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  );
}