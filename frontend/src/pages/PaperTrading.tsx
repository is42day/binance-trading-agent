import { usePaperTradingStatus, usePaperTradingSignals, usePaperTradingTrades } from '../hooks/useApi';
import MetricCard from '../components/MetricCard';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorMessage from '../components/ErrorMessage';

function fmt(n: number | undefined, d = 2) {
  if (n === undefined || n === null) return 'N/A';
  return n.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
}

export default function PaperTrading() {
  const { data: status, isLoading: statusLoading, isError: statusError } = usePaperTradingStatus();
  const { data: signals, isLoading: signalsLoading, isError: signalsError } = usePaperTradingSignals(20);
  const { data: trades, isLoading: tradesLoading, isError: tradesError } = usePaperTradingTrades(20);

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-white">Paper Trading</h2>

      {statusLoading ? (
        <LoadingSpinner />
      ) : statusError ? (
        <ErrorMessage />
      ) : (
        <>
          <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
            <div className="flex items-center gap-3 mb-4">
              <span className={`w-3 h-3 rounded-full ${status?.active ? 'bg-green-500' : 'bg-gray-500'}`} />
              <span className="text-white font-semibold">
                Paper Trading {status?.active ? 'Active' : 'Inactive'}
              </span>
              {status?.last_update && (
                <span className="text-gray-400 text-xs ml-auto">
                  Last update: {new Date(status.last_update).toLocaleString()}
                </span>
              )}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <MetricCard title="Balance" value={`$${fmt(status?.balance)}`} />
            <MetricCard
              title="Total P&L"
              value={`$${fmt(status?.total_pnl)}`}
              valueClass={(status?.total_pnl ?? 0) >= 0 ? 'text-green-400' : 'text-red-400'}
            />
            <MetricCard
              title="Win Rate"
              value={`${fmt(status?.win_rate ? status.win_rate * 100 : 0)}%`}
            />
            <MetricCard title="Total Trades" value={status?.total_trades ?? 0} />
          </div>
        </>
      )}

      <div className="bg-gray-800 rounded-lg border border-gray-700">
        <div className="p-4 border-b border-gray-700">
          <h3 className="text-lg font-semibold text-white">Recent Signals</h3>
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
                  <th className="px-4 py-3 text-left">Signal</th>
                  <th className="px-4 py-3 text-right">Confidence</th>
                  <th className="px-4 py-3 text-right">Price</th>
                  <th className="px-4 py-3 text-left">Time</th>
                </tr>
              </thead>
              <tbody>
                {signals && signals.length > 0 ? (
                  signals.map((s, i) => (
                    <tr key={i} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                      <td className="px-4 py-2 text-white font-medium">{s.symbol}</td>
                      <td className={`px-4 py-2 font-medium ${s.signal?.toUpperCase() === 'BUY' ? 'text-green-400' : s.signal?.toUpperCase() === 'SELL' ? 'text-red-400' : 'text-yellow-400'}`}>
                        {s.signal?.toUpperCase()}
                      </td>
                      <td className="px-4 py-2 text-right text-gray-300">{fmt(s.confidence ? s.confidence * 100 : 0)}%</td>
                      <td className="px-4 py-2 text-right text-gray-300">{s.price ? `$${fmt(s.price)}` : '—'}</td>
                      <td className="px-4 py-2 text-gray-400 text-xs">
                        {s.timestamp ? new Date(s.timestamp).toLocaleString() : '—'}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-500">No signals found</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="bg-gray-800 rounded-lg border border-gray-700">
        <div className="p-4 border-b border-gray-700">
          <h3 className="text-lg font-semibold text-white">Recent Paper Trades</h3>
        </div>
        {tradesLoading ? (
          <LoadingSpinner />
        ) : tradesError ? (
          <ErrorMessage />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-400 border-b border-gray-700">
                  <th className="px-4 py-3 text-left">Symbol</th>
                  <th className="px-4 py-3 text-left">Side</th>
                  <th className="px-4 py-3 text-right">Quantity</th>
                  <th className="px-4 py-3 text-right">Price</th>
                  <th className="px-4 py-3 text-right">P&L</th>
                  <th className="px-4 py-3 text-left">Time</th>
                </tr>
              </thead>
              <tbody>
                {trades && trades.length > 0 ? (
                  trades.map((t, i) => (
                    <tr key={i} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                      <td className="px-4 py-2 text-white font-medium">{t.symbol}</td>
                      <td className={`px-4 py-2 font-medium ${t.side?.toUpperCase() === 'BUY' ? 'text-green-400' : 'text-red-400'}`}>
                        {t.side?.toUpperCase()}
                      </td>
                      <td className="px-4 py-2 text-right text-gray-300">{fmt(t.quantity, 6)}</td>
                      <td className="px-4 py-2 text-right text-gray-300">${fmt(t.price)}</td>
                      <td className={`px-4 py-2 text-right ${(t.pnl ?? 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {t.pnl !== undefined ? `$${fmt(t.pnl)}` : '—'}
                      </td>
                      <td className="px-4 py-2 text-gray-400 text-xs">
                        {t.timestamp ? new Date(t.timestamp).toLocaleString() : '—'}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-500">No trades found</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
