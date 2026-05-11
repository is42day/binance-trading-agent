import { useState } from 'react';
import { usePaperTradingStatus, usePaperTradingSignals, usePaperTradingTrades, useResetPaperPortfolio } from '../hooks/useApi';
import type { PaperTradeRecord } from '../types';
import MetricCard from '../components/MetricCard';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorMessage from '../components/ErrorMessage';

function fmt(n: number | undefined, d = 2) {
  if (n === undefined || n === null) return 'N/A';
  return n.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
}

export default function PaperTrading() {
  const { data: status, isLoading: statusLoading, isError: statusError, refetch } = usePaperTradingStatus();
  const { data: signals, isLoading: signalsLoading, isError: signalsError } = usePaperTradingSignals(20);
  const { data: trades, isLoading: tradesLoading, isError: tradesError } = usePaperTradingTrades(20);
  const resetPortfolio = useResetPaperPortfolio();
  const [resetMsg, setResetMsg] = useState<{ text: string; ok: boolean } | null>(null);

  const handleReset = async () => {
    if (!window.confirm('Reset paper portfolio to $10,000? All history will be archived.')) return;
    setResetMsg(null);
    try {
      await resetPortfolio.mutateAsync(10000);
      setResetMsg({ text: 'Portfolio reset to $10,000.', ok: true });
      refetch();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setResetMsg({ text: `Error: ${msg}`, ok: false });
    }
  };

  const portfolio = status?.portfolio;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-white">Paper Trading</h2>
        <button
          onClick={handleReset}
          disabled={resetPortfolio.isPending}
          className="px-4 py-2 rounded-lg text-sm font-semibold bg-orange-700 hover:bg-orange-600 text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {resetPortfolio.isPending ? 'Resetting…' : '↺ Reset Paper Portfolio'}
        </button>
      </div>

      {resetMsg && (
        <div className={`text-sm px-3 py-2 rounded ${resetMsg.ok ? 'bg-green-900/40 text-green-300' : 'bg-red-900/40 text-red-300'}`}>
          {resetMsg.text}
        </div>
      )}

      {statusLoading ? (
        <LoadingSpinner />
      ) : statusError ? (
        <ErrorMessage />
      ) : (
        <>
          <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
            <div className="flex items-center gap-3 mb-4">
              <span className={`w-3 h-3 rounded-full ${status?.active ? 'bg-green-500 animate-pulse' : 'bg-gray-500'}`} />
              <span className="text-white font-semibold">
                Paper Trading {status?.active ? 'Active' : 'Inactive'}
              </span>
              {status?.last_update && (
                <span className="text-gray-400 text-xs ml-auto">
                  Last update: {new Date(status.last_update).toLocaleString()}
                </span>
              )}
            </div>
            {status?.message && (
              <p className="text-gray-400 text-sm">{status.message}</p>
            )}
            {status?.signals_count !== undefined && (
              <p className="text-gray-400 text-sm mt-1">Total signals generated: <span className="text-white">{status.signals_count}</span></p>
            )}
          </div>

          {portfolio ? (
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
              <MetricCard title="Balance" value={`$${fmt(portfolio.current_balance)}`} />
              <MetricCard
                title="Total P&L"
                value={`$${fmt(portfolio.total_pnl)}`}
                subtitle={`${fmt(portfolio.total_pnl_percent)}%`}
                valueClass={(portfolio.total_pnl ?? 0) >= 0 ? 'text-green-400' : 'text-red-400'}
              />
              <MetricCard
                title="Win Rate"
                value={`${fmt(portfolio.win_rate)}%`}
                valueClass={(portfolio.win_rate ?? 0) >= 50 ? 'text-green-400' : 'text-red-400'}
              />
              <MetricCard title="Total Trades" value={portfolio.total_trades ?? 0} />
            </div>
          ) : (
            <div className="bg-gray-800 rounded-lg border border-gray-700 p-6 text-center text-gray-400">
              No portfolio data available. Start paper trading to see metrics.
            </div>
          )}
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
                        <td className="px-4 py-2 text-right text-gray-300">{fmt((s.confidence as number | undefined) ? (s.confidence as number) * 100 : 0)}%</td>
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
                  <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-500">No signals found</td></tr>
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
                  <th className="px-4 py-3 text-right">Entry Price</th>
                  <th className="px-4 py-3 text-right">P&L</th>
                  <th className="px-4 py-3 text-left">Time</th>
                </tr>
              </thead>
              <tbody>
                {trades && trades.length > 0 ? (
                  trades.map((item: PaperTradeRecord, i) => {
                    // paper trades may be nested: {event, timestamp, trade: {...}}
                    // or flat when stored directly
                    const t = item.trade ?? item;
                    const side = t.side?.toUpperCase();
                    const pnl = t.pnl;
                    const entryPrice = item.trade?.entry_price ?? item.price;
                    return (
                      <tr key={i} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                        <td className="px-4 py-2 text-white font-medium">{t.symbol}</td>
                        <td className={`px-4 py-2 font-medium ${side === 'BUY' ? 'text-green-400' : 'text-red-400'}`}>
                          {side ?? '—'}
                        </td>
                        <td className="px-4 py-2 text-right text-gray-300">{fmt(t.quantity, 6)}</td>
                        <td className="px-4 py-2 text-right text-gray-300">${fmt(entryPrice)}</td>
                        <td className={`px-4 py-2 text-right ${(pnl ?? 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {pnl !== undefined ? `$${fmt(pnl)}` : '—'}
                        </td>
                        <td className="px-4 py-2 text-gray-400 text-xs">
                          {item.timestamp ? new Date(item.timestamp).toLocaleString() : '—'}
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-500">No paper trades found</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
