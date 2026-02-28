import { useRiskStatus, useTrailingStops, useSystemConfig } from '../hooks/useApi';
import MetricCard from '../components/MetricCard';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorMessage from '../components/ErrorMessage';

function fmt(n: number | undefined, d = 2) {
  if (n === undefined || n === null) return 'N/A';
  return n.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
}

export default function SignalsRisk() {
  const { data: risk, isLoading: riskLoading, isError: riskError } = useRiskStatus();
  const { data: stops, isLoading: stopsLoading, isError: stopsError } = useTrailingStops();
  const { data: config } = useSystemConfig();

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-white">Signals & Risk</h2>

      {riskLoading ? (
        <LoadingSpinner />
      ) : riskError ? (
        <ErrorMessage />
      ) : (
        <>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <MetricCard
              title="Emergency Stop"
              value={risk?.emergency_stop ? 'ACTIVE' : 'OFF'}
              valueClass={risk?.emergency_stop ? 'text-red-400' : 'text-green-400'}
            />
            <MetricCard
              title="Current Drawdown"
              value={`${fmt(risk?.current_drawdown ? risk.current_drawdown * 100 : 0)}%`}
              valueClass={(risk?.current_drawdown ?? 0) > (risk?.max_drawdown_limit ?? 1) * 0.8 ? 'text-red-400' : 'text-white'}
            />
            <MetricCard
              title="Daily Trades"
              value={`${risk?.daily_trades ?? 0} / ${risk?.max_daily_trades ?? 'N/A'}`}
            />
            <MetricCard
              title="Max Drawdown Limit"
              value={`${fmt(risk?.max_drawdown_limit ? risk.max_drawdown_limit * 100 : 0)}%`}
            />
          </div>

          {config && (
            <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
              <h3 className="text-lg font-semibold text-white mb-3">Risk Configuration</h3>
              <div className="grid grid-cols-2 gap-3 lg:grid-cols-3 text-sm">
                {Object.entries(config)
                  .filter(([, v]) => typeof v !== 'object' || Array.isArray(v))
                  .map(([k, v]) => (
                    <div key={k} className="bg-gray-700/50 rounded p-2">
                      <p className="text-gray-400 text-xs">{k.replace(/_/g, ' ')}</p>
                      <p className="text-white font-medium">
                        {Array.isArray(v) ? v.join(', ') : String(v)}
                      </p>
                    </div>
                  ))}
              </div>
            </div>
          )}
        </>
      )}

      <div className="bg-gray-800 rounded-lg border border-gray-700">
        <div className="p-4 border-b border-gray-700">
          <h3 className="text-lg font-semibold text-white">Trailing Stops</h3>
        </div>
        {stopsLoading ? (
          <LoadingSpinner />
        ) : stopsError ? (
          <ErrorMessage />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-400 border-b border-gray-700">
                  <th className="px-4 py-3 text-left">Symbol</th>
                  <th className="px-4 py-3 text-right">Entry Price</th>
                  <th className="px-4 py-3 text-right">Current Price</th>
                  <th className="px-4 py-3 text-right">Stop Price</th>
                  <th className="px-4 py-3 text-right">Trail %</th>
                  <th className="px-4 py-3 text-right">P&L</th>
                </tr>
              </thead>
              <tbody>
                {stops && stops.length > 0 ? (
                  stops.map((s, i) => (
                    <tr key={i} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                      <td className="px-4 py-2 text-white font-medium">{s.symbol}</td>
                      <td className="px-4 py-2 text-right text-gray-300">${fmt(s.entry_price)}</td>
                      <td className="px-4 py-2 text-right text-gray-300">${fmt(s.current_price)}</td>
                      <td className="px-4 py-2 text-right text-yellow-400">${fmt(s.stop_price)}</td>
                      <td className="px-4 py-2 text-right text-gray-300">{fmt(s.trail_percent)}%</td>
                      <td className={`px-4 py-2 text-right ${(s.pnl ?? 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {s.pnl !== undefined ? `$${fmt(s.pnl)}` : '—'}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-500">No trailing stops active</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
