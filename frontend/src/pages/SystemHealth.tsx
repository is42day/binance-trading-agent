import { useSystemConfig, useHealthCheck, useReadyCheck } from '../hooks/useApi';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorMessage from '../components/ErrorMessage';

function StatusBadge({ ok, label }: { ok: boolean | string | undefined; label: string }) {
  const isOk = ok === true || ok === 'ready' || ok === 'healthy' || ok === 'ok';
  const displayText = typeof ok === 'string' ? ok : (isOk ? 'OK' : 'FAIL');
  return (
    <div className="flex items-center gap-2">
      <span className={`w-2 h-2 rounded-full flex-shrink-0 ${isOk ? 'bg-green-500' : 'bg-red-500'}`} />
      <span className="text-gray-300 text-sm">{label}</span>
      <span className={`ml-auto text-xs font-medium truncate max-w-[140px] ${isOk ? 'text-green-400' : 'text-red-400'}`}>
        {displayText}
      </span>
    </div>
  );
}

export default function SystemHealth() {
  const { data: config, isLoading: configLoading, isError: configError } = useSystemConfig();
  const { data: health, isLoading: healthLoading, isError: healthError } = useHealthCheck();
  const { data: ready, isLoading: readyLoading, isError: readyError } = useReadyCheck();

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-white">System Health</h2>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
          <h3 className="text-lg font-semibold text-white mb-4">Health Check</h3>
          {healthLoading ? (
            <LoadingSpinner />
          ) : healthError ? (
            <ErrorMessage message="Health check failed — API may be offline." />
          ) : (
            <div className="space-y-3">
              <StatusBadge ok={health?.status === 'healthy' || health?.status === 'ok'} label="API Status" />
              <StatusBadge ok={health?.checks?.database} label="Database" />
              <StatusBadge ok={health?.checks?.schema} label="Schema" />
            </div>
          )}
        </div>

        <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
          <h3 className="text-lg font-semibold text-white mb-4">Readiness Check</h3>
          {readyLoading ? (
            <LoadingSpinner />
          ) : readyError ? (
            <ErrorMessage message="Readiness check failed." />
          ) : (
            <div className="space-y-3">
              <StatusBadge ok={ready?.ready} label="Overall Ready" />
              <StatusBadge ok={ready?.checks?.database} label="Database" />
              <StatusBadge ok={ready?.checks?.binance_api} label="Binance API" />
              <StatusBadge ok={ready?.checks?.cache} label="Cache" />
            </div>
          )}
        </div>

        <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
          <h3 className="text-lg font-semibold text-white mb-4">System Config</h3>
          {configLoading ? (
            <LoadingSpinner />
          ) : configError ? (
            <ErrorMessage />
          ) : (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-gray-400 text-sm">Demo Mode</span>
                <span className={`text-sm font-medium ${config?.demo_mode ? 'text-yellow-400' : 'text-gray-400'}`}>
                  {config?.demo_mode ? 'Enabled' : 'Disabled'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-400 text-sm">Testnet</span>
                <span className={`text-sm font-medium ${config?.binance_testnet ? 'text-yellow-400' : 'text-gray-400'}`}>
                  {config?.binance_testnet ? 'Enabled' : 'Disabled'}
                </span>
              </div>
              {config?.supported_symbols && (
                <div>
                  <p className="text-gray-400 text-sm mb-1">Supported Symbols</p>
                  <div className="flex flex-wrap gap-1">
                    {config.supported_symbols.map(s => (
                      <span key={s} className="bg-blue-900/40 border border-blue-700 text-blue-300 text-xs px-2 py-0.5 rounded">
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {config && (
        <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
          <h3 className="text-lg font-semibold text-white mb-3">All Config Values</h3>
          <div className="grid grid-cols-2 gap-2 lg:grid-cols-3 text-sm">
            {Object.entries(config).map(([k, v]) => (
              <div key={k} className="bg-gray-700/50 rounded p-2">
                <p className="text-gray-400 text-xs capitalize">{k.replace(/_/g, ' ')}</p>
                <p className="text-white font-medium truncate">
                  {Array.isArray(v) ? v.join(', ') : typeof v === 'object' ? JSON.stringify(v) : String(v)}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
