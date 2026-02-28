import { NavLink } from 'react-router-dom';
import { useHealthCheck } from '../hooks/useApi';

const navItems = [
  { to: '/', label: 'Dashboard', icon: '📊' },
  { to: '/market', label: 'Market Data', icon: '📈' },
  { to: '/paper-trading', label: 'Paper Trading', icon: '📝' },
  { to: '/signals', label: 'Signals & Risk', icon: '🚦' },
  { to: '/performance', label: 'Performance', icon: '🏆' },
  { to: '/health', label: 'System Health', icon: '💚' },
];

export default function Navbar() {
  const { data: health, isError } = useHealthCheck();
  const isOnline = !isError && health?.status === 'ok';

  return (
    <aside className="w-64 min-h-screen bg-gray-900 border-r border-gray-700 flex flex-col">
      <div className="p-4 border-b border-gray-700">
        <h1 className="text-white font-bold text-sm leading-tight">Binance Trading Agent</h1>
        <div className="flex items-center gap-2 mt-2">
          <span className={`w-2 h-2 rounded-full ${isOnline ? 'bg-green-500' : 'bg-red-500'}`} />
          <span className="text-xs text-gray-400">{isOnline ? 'API Online' : 'API Offline'}</span>
        </div>
      </div>
      <nav className="flex-1 p-3 space-y-1">
        {navItems.map(({ to, label, icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                isActive
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:bg-gray-800 hover:text-white'
              }`
            }
          >
            <span>{icon}</span>
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
