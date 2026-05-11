import { useState } from 'react';
import { useOperatorStatus, useTriggerEmergencyStop, useResumeTrading, useReconcileOrders, useCancelStaleOrders } from '../hooks/useApi';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorMessage from '../components/ErrorMessage';
import type { RuntimeMode, StreamFreshnessItem, OpenOrderItem } from '../types';

// ---------------------------------------------------------------------------
// Small helpers
// ---------------------------------------------------------------------------

const RUNTIME_MODE_STYLES: Record<RuntimeMode | string, string> = {
  demo: 'bg-gray-700 text-gray-300',
  testnet: 'bg-yellow-900/50 text-yellow-300 border border-yellow-700',
  live_blocked: 'bg-red-900/50 text-red-300 border border-red-700',
  live_armed: 'bg-green-900/50 text-green-300 border border-green-600',
};

function RuntimeBadge({ mode }: { mode: string }) {
  const cls = RUNTIME_MODE_STYLES[mode] ?? 'bg-gray-700 text-gray-300';
  return (
    <span className={`px-3 py-1 rounded-full text-sm font-bold uppercase tracking-wider ${cls}`}>
      {mode.replace(/_/g, ' ')}
    </span>
  );
}

function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
      <h3 className="text-lg font-semibold text-white mb-4">{title}</h3>
      {children}
    </div>
  );
}

function Row({ label, value, highlight }: { label: string; value: React.ReactNode; highlight?: boolean }) {
  return (
    <div className="flex items-center justify-between py-1 border-b border-gray-700/50 last:border-0">
      <span className="text-gray-400 text-sm">{label}</span>
      <span className={`text-sm font-medium ${highlight ? 'text-yellow-400' : 'text-white'}`}>{value}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-sections
// ---------------------------------------------------------------------------

function CircuitBreakerSection({ cb }: { cb: { state: string; failure_count?: number; last_failure?: string | null; error?: string } }) {
  if (cb.error) return <ErrorMessage message={cb.error} />;
  const isOpen = cb.state === 'open';
  return (
    <div className="space-y-2">
      <Row
        label="State"
        value={
          <span className={isOpen ? 'text-red-400 font-bold' : 'text-green-400'}>
            {cb.state.toUpperCase()}
          </span>
        }
      />
      <Row label="Failures" value={cb.failure_count ?? 0} highlight={(cb.failure_count ?? 0) > 0} />
      {cb.last_failure && <Row label="Last Failure" value={new Date(cb.last_failure).toLocaleTimeString()} />}
    </div>
  );
}

function RateLimitSection({ rl }: { rl: { weight_used: number; weight_budget: number; weight_utilization_pct: number; in_holdoff: boolean; retry_after_remaining: number | null; orders_this_second: number; order_budget_per_sec: number; error?: string } }) {
  if (rl.error) return <ErrorMessage message={rl.error} />;
  const utilPct = rl.weight_utilization_pct;
  const barColor = utilPct >= 90 ? 'bg-red-500' : utilPct >= 70 ? 'bg-yellow-500' : 'bg-green-500';
  return (
    <div className="space-y-3">
      <div>
        <div className="flex justify-between text-xs text-gray-400 mb-1">
          <span>Weight usage</span>
          <span className={utilPct >= 70 ? 'text-yellow-400' : 'text-green-400'}>
            {rl.weight_used} / {rl.weight_budget} ({utilPct.toFixed(1)}%)
          </span>
        </div>
        <div className="w-full bg-gray-700 rounded-full h-2">
          <div className={`${barColor} h-2 rounded-full transition-all`} style={{ width: `${Math.min(utilPct, 100)}%` }} />
        </div>
      </div>
      <Row label="Orders/sec" value={`${rl.orders_this_second} / ${rl.order_budget_per_sec}`} />
      {rl.in_holdoff && (
        <div className="text-red-400 text-sm font-medium">
          ⛔ Rate-limit holdoff — retry in {rl.retry_after_remaining?.toFixed(1)}s
        </div>
      )}
    </div>
  );
}

function StreamFreshnessSection({ streams }: { streams: StreamFreshnessItem[] | { error?: string } }) {
  if (!Array.isArray(streams)) return <ErrorMessage message={(streams as { error?: string }).error} />;
  if (streams.length === 0) return <p className="text-gray-500 text-sm">No active streams.</p>;
  return (
    <div className="space-y-2">
      {streams.map((s) => (
        <div key={`${s.symbol}-${s.interval}`} className="flex items-center gap-2 text-sm">
          <span className={`w-2 h-2 rounded-full flex-shrink-0 ${s.connected && !s.is_stale ? 'bg-green-500' : 'bg-red-500'}`} />
          <span className="text-gray-300 font-mono">{s.symbol}@{s.interval}</span>
          <span className={`ml-auto text-xs ${s.is_stale ? 'text-red-400' : 'text-gray-400'}`}>
            {s.age_seconds !== null ? `${s.age_seconds.toFixed(0)}s ago` : 'no data'}
            {s.is_stale && ' ⚠ stale'}
          </span>
          {s.reconnect_attempts > 0 && (
            <span className="text-yellow-500 text-xs">↻{s.reconnect_attempts}</span>
          )}
        </div>
      ))}
    </div>
  );
}

function ValidationGateSection({ gate }: { gate: { generated_at: string | null; result: string | null; strategy: string | null; symbols: string[] | null; error?: string } | null }) {
  if (!gate) return <p className="text-gray-500 text-sm">No gate artifact found.</p>;
  if (gate.error) return <ErrorMessage message={gate.error} />;
  const cleared = gate.result === 'pass' || gate.result === 'cleared';
  return (
    <div className="space-y-2">
      <Row label="Result" value={
        <span className={cleared ? 'text-green-400' : 'text-red-400'}>
          {gate.result?.toUpperCase() ?? 'UNKNOWN'}
        </span>
      } />
      {gate.strategy && <Row label="Strategy" value={gate.strategy} />}
      {gate.generated_at && <Row label="Generated at" value={new Date(gate.generated_at).toLocaleString()} />}
      {gate.symbols && (
        <div className="flex flex-wrap gap-1 pt-1">
          {gate.symbols.map((s) => (
            <span key={s} className="bg-blue-900/40 border border-blue-700 text-blue-300 text-xs px-2 py-0.5 rounded">{s}</span>
          ))}
        </div>
      )}
    </div>
  );
}

function ExecutionPolicySection({ policy }: { policy: { execution_mode: string; max_spread_pct: number; max_slippage_pct: number; limit_price_offset_bps: number; stale_order_seconds: number; error?: string } }) {
  if (policy.error) return <ErrorMessage message={policy.error} />;
  return (
    <div className="space-y-2">
      <Row label="Mode" value={<span className="text-blue-300 font-medium">{policy.execution_mode}</span>} />
      <Row label="Max spread" value={`${policy.max_spread_pct}%`} />
      <Row label="Max slippage" value={`${policy.max_slippage_pct}%`} />
      <Row label="Limit offset" value={`${policy.limit_price_offset_bps} bps`} />
      <Row label="Stale after" value={`${policy.stale_order_seconds}s`} />
    </div>
  );
}

function OpenOrdersSection({ orders, count, staleCount }: { orders: OpenOrderItem[] | { error?: string }; count: number; staleCount: number }) {
  if (!Array.isArray(orders)) return <ErrorMessage message={(orders as { error?: string }).error} />;
  return (
    <div>
      <div className="flex gap-4 mb-3 text-sm">
        <span className="text-gray-400">Open: <strong className="text-white">{count}</strong></span>
        {staleCount > 0 && <span className="text-yellow-400">Stale: <strong>{staleCount}</strong></span>}
      </div>
      {orders.length === 0 ? (
        <p className="text-gray-500 text-sm">No open orders.</p>
      ) : (
        <div className="space-y-2 max-h-48 overflow-y-auto">
          {orders.map((o) => (
            <div key={o.client_order_id} className={`flex items-center gap-2 text-xs rounded px-2 py-1 ${o.stale ? 'bg-yellow-900/30 border border-yellow-700/50' : 'bg-gray-700/50'}`}>
              <span className={`font-medium ${o.side === 'BUY' ? 'text-green-400' : 'text-red-400'}`}>{o.side}</span>
              <span className="text-gray-300 font-mono">{o.symbol}</span>
              <span className="text-gray-400">{o.status}</span>
              <span className="text-gray-400 ml-auto">{o.executed_quantity}/{o.quantity}</span>
              {o.stale && <span className="text-yellow-400">⚠</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function LastBlockedSection({ blocked }: { blocked: { symbol?: string; action?: string; blocked_reason: string; timestamp?: string; [key: string]: unknown } | null }) {
  if (!blocked) return <p className="text-gray-500 text-sm">No recent blocked trades.</p>;
  return (
    <div className="space-y-2">
      <Row label="Reason" value={<span className="text-orange-400 font-mono text-xs break-all">{blocked.blocked_reason}</span>} />
      {blocked.symbol && <Row label="Symbol" value={String(blocked.symbol)} />}
      {blocked.action && <Row label="Action" value={String(blocked.action)} />}
      {blocked.timestamp && <Row label="Time" value={new Date(String(blocked.timestamp)).toLocaleString()} />}
    </div>
  );
}

function EmergencyStopSection({ es }: { es: { enabled: boolean; reason: string | null; error?: string } }) {
  if (es.error) return <ErrorMessage message={es.error} />;
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-3">
        <span className={`w-3 h-3 rounded-full ${es.enabled ? 'bg-red-500 animate-pulse' : 'bg-green-500'}`} />
        <span className={`text-base font-bold ${es.enabled ? 'text-red-400' : 'text-green-400'}`}>
          {es.enabled ? 'ACTIVE — ALL TRADING HALTED' : 'Inactive'}
        </span>
      </div>
      {es.enabled && es.reason && (
        <div className="mt-2 text-sm text-red-300 bg-red-900/30 rounded px-3 py-2 border border-red-700">
          {es.reason}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function OperatorStatus() {
  const { data, isLoading, isError, dataUpdatedAt, refetch } = useOperatorStatus();
  const emergencyStop = useTriggerEmergencyStop();
  const resumeTrading = useResumeTrading();
  const reconcile = useReconcileOrders();
  const cancelStale = useCancelStaleOrders();

  const [actionMsg, setActionMsg] = useState<{ text: string; ok: boolean } | null>(null);

  const runAction = async (
    fn: () => Promise<unknown>,
    successMsg: string,
  ) => {
    setActionMsg(null);
    try {
      await fn();
      setActionMsg({ text: successMsg, ok: true });
      refetch();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setActionMsg({ text: `Error: ${msg}`, ok: false });
    }
  };

  const isEmergencyActive = data?.emergency_stop?.enabled ?? false;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-white">Operator Status</h2>
        {dataUpdatedAt > 0 && (
          <span className="text-xs text-gray-500">
            Updated {new Date(dataUpdatedAt).toLocaleTimeString()}
          </span>
        )}
      </div>

      {/* Action buttons */}
      <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
        <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">Actions</h3>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={() => runAction(
              () => emergencyStop.mutateAsync('Operator triggered from dashboard'),
              'Emergency stop activated.',
            )}
            disabled={emergencyStop.isPending || isEmergencyActive}
            className="px-4 py-2 rounded-lg text-sm font-semibold bg-red-700 hover:bg-red-600 text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {emergencyStop.isPending ? 'Stopping…' : '🛑 Emergency Stop'}
          </button>

          <button
            onClick={() => runAction(
              () => resumeTrading.mutateAsync(),
              'Trading resumed.',
            )}
            disabled={resumeTrading.isPending || !isEmergencyActive}
            className="px-4 py-2 rounded-lg text-sm font-semibold bg-green-700 hover:bg-green-600 text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {resumeTrading.isPending ? 'Resuming…' : '▶ Resume Trading'}
          </button>

          <button
            onClick={() => runAction(
              () => reconcile.mutateAsync(),
              'Reconciliation complete.',
            )}
            disabled={reconcile.isPending}
            className="px-4 py-2 rounded-lg text-sm font-semibold bg-blue-700 hover:bg-blue-600 text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {reconcile.isPending ? 'Reconciling…' : '🔄 Reconcile Orders'}
          </button>

          <button
            onClick={() => runAction(
              () => cancelStale.mutateAsync(),
              'Stale orders cancelled.',
            )}
            disabled={cancelStale.isPending}
            className="px-4 py-2 rounded-lg text-sm font-semibold bg-yellow-700 hover:bg-yellow-600 text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {cancelStale.isPending ? 'Cancelling…' : '✂ Cancel Stale Orders'}
          </button>
        </div>

        {actionMsg && (
          <div className={`mt-3 text-sm px-3 py-2 rounded ${actionMsg.ok ? 'bg-green-900/40 text-green-300' : 'bg-red-900/40 text-red-300'}`}>
            {actionMsg.text}
          </div>
        )}
      </div>

      {isLoading && <LoadingSpinner />}
      {isError && <ErrorMessage message="Failed to load operator status — API may be offline." />}

      {data && (
        <>
          {/* Top row: armed status + emergency stop */}
          <div className="flex flex-wrap gap-4 items-center">
            <div className="bg-gray-800 rounded-lg border border-gray-700 px-5 py-3 flex items-center gap-3">
              <span className="text-gray-400 text-sm">Runtime mode</span>
              <RuntimeBadge mode={data.runtime_mode} />
            </div>
            {data.emergency_stop.enabled && (
              <div className="flex-1 bg-red-900/30 rounded-lg border border-red-700 px-4 py-3 flex items-center gap-3">
                <span className="w-3 h-3 rounded-full bg-red-500 animate-pulse" />
                <span className="text-red-300 font-bold">EMERGENCY STOP ACTIVE</span>
                {data.emergency_stop.reason && (
                  <span className="text-red-400 text-sm">— {data.emergency_stop.reason}</span>
                )}
              </div>
            )}
          </div>

          {/* Main grid */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 xl:grid-cols-3">
            <SectionCard title="Circuit Breaker">
              <CircuitBreakerSection cb={data.circuit_breaker} />
            </SectionCard>

            <SectionCard title="Rate Limits">
              <RateLimitSection rl={data.rate_limits} />
            </SectionCard>

            <SectionCard title="Emergency Stop">
              <EmergencyStopSection es={data.emergency_stop} />
            </SectionCard>

            <SectionCard title="Stream Freshness">
              <StreamFreshnessSection streams={data.stream_freshness} />
            </SectionCard>

            <SectionCard title="Strategy Validation Gate">
              <ValidationGateSection gate={data.validation_gate} />
            </SectionCard>

            <SectionCard title="Execution Policy">
              <ExecutionPolicySection policy={data.execution_policy} />
            </SectionCard>
          </div>

          {/* Full-width sections */}
          <SectionCard title={`Open Orders (${data.open_orders_count}${data.stale_orders_count > 0 ? ` · ${data.stale_orders_count} stale` : ''})`}>
            <OpenOrdersSection orders={data.open_orders} count={data.open_orders_count} staleCount={data.stale_orders_count} />
          </SectionCard>

          <SectionCard title="Last Blocked Trade">
            <LastBlockedSection blocked={data.last_blocked_trade} />
          </SectionCard>
        </>
      )}
    </div>
  );
}
