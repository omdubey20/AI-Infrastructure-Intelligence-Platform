import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
const nav = [
  { path: '/', label: 'Dashboard' },
  { path: '/servers', label: 'Servers' },
  { path: '/projects', label: 'Projects' },
  { path: '/cleanup', label: 'Cleanup' },
];
export default function Sidebar() {
  const { logout } = useAuth();
  const loc = useLocation();
  return (
    <aside className='w-64 min-h-screen bg-slate-900 border-r border-slate-700 flex flex-col'>
      <div className='p-6 border-b border-slate-700'>
        <h1 className='text-xl font-bold text-white'>ServerManager Pro</h1>
        <p className='text-slate-400 text-sm'>Management Console</p>
      </div>
      <nav className='flex-1 p-4 space-y-1'>
        {nav.map(item => (
          <Link key={item.path} to={item.path} className={`flex items-center px-4 py-3 rounded-lg text-sm font-medium transition-colors ${loc.pathname === item.path ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-800 hover:text-white'}`}>
            {item.label}
          </Link>
        ))}
      </nav>
      <div className='p-4 border-t border-slate-700'>
        <button onClick={logout} className='w-full px-4 py-2 text-sm text-slate-300 hover:text-white hover:bg-slate-800 rounded-lg text-left'>Logout</button>
      </div>
    </aside>
  );
}
