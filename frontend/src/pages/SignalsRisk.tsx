import { useRiskStatus, useTrailingStops, useSystemConfig, usePaperTradingSignals } from '../hooks/useApi';
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
  const { data: signals, isLoading: signalsLoading, isError: signalsError } = usePaperTradingSignals(30);

  const stopEntries = stops?.positions ? Object.entries(stops.positions) : [];

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
              value={`$${fmt(risk?.current_drawdown ?? 0)}`}
              valueClass={(risk?.current_drawdown ?? 0) > 0 ? 'text-red-400' : 'text-white'}
            />
            <MetricCard
              title="Daily Trades"
              value={String(risk?.daily_trades ?? 0)}
            />
            <MetricCard
              title="Active Risk Rules"
              value={String(risk?.risk_rules_active ?? 0)}
            />
          </div>

          <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
            <MetricCard
              title="Consecutive Losses"
              value={String(risk?.consecutive_losses ?? 0)}
              valueClass={(risk?.consecutive_losses ?? 0) > 2 ? 'text-yellow-400' : 'text-white'}
            />
            <MetricCard
              title="Trailing Stops Active"
              value={String(risk?.trailing_stops_active ?? stops?.active_stops ?? 0)}
            />
            <MetricCard
              title="Recent Trades Count"
              value={String(risk?.recent_trades_count ?? 0)}
            />
          </div>

          {config?.risk_config && (
            <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
              <h3 className="text-lg font-semibold text-white mb-3">Risk Configuration</h3>
              <div className="grid grid-cols-2 gap-3 lg:grid-cols-3 text-sm">
                {Object.entries(config.risk_config as Record<string, unknown>).map(([k, v]) => (
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
          <h3 className="text-lg font-semibold text-white">Recent Trading Signals</h3>
        </div>
        {signalsLoading ? (
          <LoadingSpinner />
        ) : signalsError ? (
          <ErrorMessage />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-400 border-b border-gray-700">
                  <th className="px-4 py-3 text-left">Symbol</th>
                  <th className="px-4 py-3 text-left">Action</th>
                  <th className="px-4 py-3 text-left">Strategy</th>
                  <th className="px-4 py-3 text-right">Confidence</th>
                  <th className="px-4 py-3 text-left">Executed</th>
                  <th className="px-4 py-3 text-left">Time</th>
                </tr>
              </thead>
              <tbody>
                {signals && signals.length > 0 ? (
                  signals.map((s, i) => {
                    const action = (s.action as string | undefined)?.toUpperCase();
                    return (
                      <tr key={i} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                        <td className="px-4 py-2 text-white font-medium">{s.symbol as string}</td>
                        <td className={`px-4 py-2 font-medium ${action === 'BUY' ? 'text-green-400' : action === 'SELL' ? 'text-red-400' : 'text-yellow-400'}`}>
                          {action ?? '—'}
                        </td>
                        <td className="px-4 py-2 text-gray-400 text-xs">{(s.strategy as string | undefined) ?? '—'}</td>
                        <td className="px-4 py-2 text-right text-gray-300">
                          {fmt((s.confidence as number | undefined) ? (s.confidence as number) * 100 : 0)}%
                        </td>
                        <td className="px-4 py-2">
                          <span className={`text-xs px-2 py-0.5 rounded ${s.executed ? 'bg-green-900/40 text-green-400' : 'bg-gray-700 text-gray-400'}`}>
                            {s.executed ? 'Yes' : 'No'}
                          </span>
                        </td>
                        <td className="px-4 py-2 text-gray-400 text-xs">
                          {s.timestamp ? new Date(s.timestamp as string).toLocaleString() : '—'}
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-500">No signals yet — start paper trading to generate signals</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="bg-gray-800 rounded-lg border border-gray-700">
        <div className="p-4 border-b border-gray-700">
          <h3 className="text-lg font-semibold text-white">
            Trailing Stops {stops?.active_stops !== undefined && `(${stops.active_stops} active)`}
          </h3>
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
                  <th className="px-4 py-3 text-left">Side</th>
                  <th className="px-4 py-3 text-right">Entry Price</th>
                  <th className="px-4 py-3 text-right">Current Stop</th>
                  <th className="px-4 py-3 text-right">Trail %</th>
                  <th className="px-4 py-3 text-right">Registered</th>
                </tr>
              </thead>
              <tbody>
                {stopEntries.length > 0 ? (
                  stopEntries.map(([symbol, s]) => (
                    <tr key={symbol} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                      <td className="px-4 py-2 text-white font-medium">{symbol}</td>
                      <td className={`px-4 py-2 font-medium ${s.side?.toLowerCase() === 'buy' ? 'text-green-400' : 'text-red-400'}`}>
                        {s.side?.toUpperCase()}
                      </td>
                      <td className="px-4 py-2 text-right text-gray-300">${fmt(s.entry_price)}</td>
                      <td className="px-4 py-2 text-right text-yellow-400">${fmt(s.current_stop)}</td>
                      <td className="px-4 py-2 text-right text-gray-300">{fmt(s.trailing_pct ? s.trailing_pct * 100 : 0)}%</td>
                      <td className="px-4 py-2 text-right text-gray-400 text-xs">
                        {s.registered_at ? new Date(s.registered_at).toLocaleString() : '—'}
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
