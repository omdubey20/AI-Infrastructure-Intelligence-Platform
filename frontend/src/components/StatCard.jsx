import React from 'react';
const colors = {
  blue: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  green: 'bg-green-500/10 text-green-400 border-green-500/20',
  yellow: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
};
export default function StatCard({ title, value, color = 'blue' }) {
  return (
    <div className={`rounded-xl border p-5 ${colors[color]}`}>
      <p className='text-xs font-medium uppercase tracking-wide opacity-70 mb-3'>{title}</p>
      <p className='text-3xl font-bold'>{value}</p>
    </div>
  );
}
