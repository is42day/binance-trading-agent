import { usePortfolioSummary, useTradeHistory } from '../hooks/useApi';
import MetricCard from '../components/MetricCard';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorMessage from '../components/ErrorMessage';

function fmt(n: number | undefined, decimals = 2) {
  if (n === undefined || n === null) return 'N/A';
  return n.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

export default function Dashboard() {
  const { data: summary, isLoading: summaryLoading, isError: summaryError } = usePortfolioSummary();
  const { data: trades, isLoading: tradesLoading, isError: tradesError } = useTradeHistory(20);

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-white">Dashboard</h2>

      {summaryLoading ? (
        <LoadingSpinner />
      ) : summaryError ? (
        <ErrorMessage />
      ) : (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <MetricCard
            title="Total Value"
            value={`$${fmt(summary?.total_value)}`}
            subtitle={`Source: ${summary?.source ?? 'N/A'}`}
          />
          <MetricCard
            title="Total P&L"
            value={`$${fmt(summary?.total_pnl)}`}
            valueClass={(summary?.total_pnl ?? 0) >= 0 ? 'text-green-400' : 'text-red-400'}
          />
          <MetricCard
            title="Open Positions"
            value={summary?.positions_count ?? 0}
          />
          <MetricCard
            title="Total Trades"
            value={summary?.number_of_trades ?? 0}
          />
        </div>
      )}

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
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-gray-500">No trades found</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
