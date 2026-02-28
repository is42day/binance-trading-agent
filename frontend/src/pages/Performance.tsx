import { usePerformanceSummary, usePerformanceTrades, usePerformanceBySymbol } from '../hooks/useApi';
import MetricCard from '../components/MetricCard';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorMessage from '../components/ErrorMessage';

function fmt(n: number | undefined, d = 2) {
  if (n === undefined || n === null) return 'N/A';
  return n.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
}

export default function Performance() {
  const { data: summary, isLoading: summaryLoading, isError: summaryError } = usePerformanceSummary();
  const { data: trades, isLoading: tradesLoading, isError: tradesError } = usePerformanceTrades(20);
  const { data: bySymbol, isLoading: bySymbolLoading, isError: bySymbolError } = usePerformanceBySymbol();

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-white">Performance</h2>

      {summaryLoading ? (
        <LoadingSpinner />
      ) : summaryError ? (
        <ErrorMessage />
      ) : (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <MetricCard
            title="Win Rate"
            value={`${fmt(summary?.win_rate ? summary.win_rate * 100 : 0)}%`}
            valueClass={(summary?.win_rate ?? 0) >= 0.5 ? 'text-green-400' : 'text-red-400'}
          />
          <MetricCard
            title="Sharpe Ratio"
            value={fmt(summary?.sharpe_ratio)}
            valueClass={(summary?.sharpe_ratio ?? 0) >= 1 ? 'text-green-400' : 'text-yellow-400'}
          />
          <MetricCard
            title="Max Drawdown"
            value={`${fmt(summary?.max_drawdown ? summary.max_drawdown * 100 : 0)}%`}
            valueClass="text-red-400"
          />
          <MetricCard
            title="Profit Factor"
            value={fmt(summary?.profit_factor)}
            valueClass={(summary?.profit_factor ?? 0) >= 1.5 ? 'text-green-400' : 'text-yellow-400'}
          />
        </div>
      )}

      <div className="bg-gray-800 rounded-lg border border-gray-700">
        <div className="p-4 border-b border-gray-700">
          <h3 className="text-lg font-semibold text-white">Performance by Symbol</h3>
        </div>
        {bySymbolLoading ? (
          <LoadingSpinner />
        ) : bySymbolError ? (
          <ErrorMessage />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-400 border-b border-gray-700">
                  <th className="px-4 py-3 text-left">Symbol</th>
                  <th className="px-4 py-3 text-right">Trades</th>
                  <th className="px-4 py-3 text-right">Win Rate</th>
                  <th className="px-4 py-3 text-right">Total P&L</th>
                  <th className="px-4 py-3 text-right">Avg P&L</th>
                </tr>
              </thead>
              <tbody>
                {bySymbol && bySymbol.length > 0 ? (
                  bySymbol.map((s, i) => (
                    <tr key={i} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                      <td className="px-4 py-2 text-white font-medium">{s.symbol}</td>
                      <td className="px-4 py-2 text-right text-gray-300">{s.trades}</td>
                      <td className="px-4 py-2 text-right text-gray-300">{fmt(s.win_rate ? s.win_rate * 100 : 0)}%</td>
                      <td className={`px-4 py-2 text-right ${s.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        ${fmt(s.total_pnl)}
                      </td>
                      <td className={`px-4 py-2 text-right ${(s.avg_pnl ?? 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {s.avg_pnl !== undefined ? `$${fmt(s.avg_pnl)}` : '—'}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-500">No data available</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="bg-gray-800 rounded-lg border border-gray-700">
        <div className="p-4 border-b border-gray-700">
          <h3 className="text-lg font-semibold text-white">Recent Trades</h3>
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
