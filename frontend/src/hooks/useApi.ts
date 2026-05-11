import axios from 'axios';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { API_BASE_URL } from '../config/api';
import type {
  PortfolioSummary,
  Position,
  Trade,
  RiskStatus,
  TrailingStopsResponse,
  MarketPrice,
  SystemConfig,
  PerformanceSummary,
  PerformanceBySymbol,
  PaperTradingStatus,
  PaperTradeRecord,
  Signal,
  HealthStatus,
  ReadyStatus,
  OperatorStatus,
} from '../types';

// If VITE_API_AUTH_TOKEN is set at build time, attach a Bearer token.
// If unset, requests are unauthenticated — rely on API_AUTH_REQUIRED=false (local/dev)
// or proxy/session auth (production). Never bake a default secret into the bundle.
const AUTH_TOKEN: string = import.meta.env.VITE_API_AUTH_TOKEN ?? '';

const api = axios.create({
  baseURL: API_BASE_URL,
  ...(AUTH_TOKEN && { headers: { Authorization: `Bearer ${AUTH_TOKEN}` } }),
});

const fetcher = async <T>(url: string): Promise<T> => {
  const { data } = await api.get<T>(url);
  return data;
};

const poster = async <T, P = unknown>(url: string, payload?: P): Promise<T> => {
  const { data } = await api.post<T>(url, payload ?? {});
  return data;
};

function useInvalidateOperatorData() {
  const queryClient = useQueryClient();
  return () => {
    void queryClient.invalidateQueries({ queryKey: ['operator'] });
    void queryClient.invalidateQueries({ queryKey: ['risk'] });
    void queryClient.invalidateQueries({ queryKey: ['paper-trading'] });
    void queryClient.invalidateQueries({ queryKey: ['portfolio'] });
  };
}

export function usePortfolioSummary() {
  return useQuery<PortfolioSummary>({
    queryKey: ['portfolio', 'summary'],
    queryFn: () => fetcher('/api/v1/portfolio/summary'),
    staleTime: 10_000,
    refetchInterval: 30_000,
  });
}

export function usePortfolioPositions() {
  return useQuery<Position[]>({
    queryKey: ['portfolio', 'positions'],
    queryFn: async () => {
      const data = await fetcher<{ positions: Position[] }>('/api/v1/portfolio/positions');
      return data.positions ?? [];
    },
    staleTime: 10_000,
    refetchInterval: 30_000,
  });
}

export function useTradeHistory(limit = 20) {
  return useQuery<Trade[]>({
    queryKey: ['portfolio', 'trade-history', limit],
    queryFn: async () => {
      const data = await fetcher<{ trades: Trade[] }>(`/api/v1/portfolio/trade-history?limit=${limit}`);
      return data.trades ?? [];
    },
    staleTime: 10_000,
    refetchInterval: 30_000,
  });
}

export function useRiskStatus() {
  return useQuery<RiskStatus>({
    queryKey: ['risk', 'status'],
    queryFn: () => fetcher('/api/v1/risk/status'),
    staleTime: 10_000,
    refetchInterval: 30_000,
  });
}

export function useTrailingStops() {
  return useQuery<TrailingStopsResponse>({
    queryKey: ['risk', 'trailing-stops'],
    queryFn: () => fetcher('/api/v1/risk/trailing-stops'),
    staleTime: 10_000,
    refetchInterval: 30_000,
  });
}

export function useMarketPrice(symbol: string) {
  return useQuery<MarketPrice>({
    queryKey: ['market', 'price', symbol],
    queryFn: () => fetcher(`/api/v1/market/price/${symbol}`),
    staleTime: 5_000,
    refetchInterval: 10_000,
  });
}

export function useSystemConfig() {
  return useQuery<SystemConfig>({
    queryKey: ['system', 'config'],
    queryFn: () => fetcher('/api/v1/system/config'),
    staleTime: 60_000,
  });
}

export function usePerformanceSummary() {
  return useQuery<PerformanceSummary>({
    queryKey: ['performance', 'summary'],
    queryFn: () => fetcher('/api/v1/performance/summary'),
    staleTime: 10_000,
    refetchInterval: 30_000,
  });
}

export function usePerformanceTrades(limit = 50) {
  return useQuery<Trade[]>({
    queryKey: ['performance', 'trades', limit],
    queryFn: async () => {
      // The performance analytics endpoint uses entry_price/entry_time field names
      // while the UI Trade type uses price/timestamp — map them here.
      interface PerformanceTradeRaw {
        symbol: string;
        side: string;
        entry_price: number;
        exit_price?: number;
        quantity: number;
        entry_time: string;
        exit_time?: string;
        pnl?: number;
        pnl_pct?: number;
        is_closed?: boolean;
        notes?: string;
      }
      const data = await fetcher<{ trades: PerformanceTradeRaw[]; total_trades: number }>(
        `/api/v1/performance/trades?limit=${limit}`
      );
      return (data.trades ?? []).map((t) => ({
        symbol: t.symbol,
        side: t.side,
        quantity: t.quantity,
        price: t.entry_price,
        timestamp: t.entry_time,
        pnl: t.pnl,
      }));
    },
    staleTime: 10_000,
    refetchInterval: 30_000,
  });
}

export function usePerformanceBySymbol() {
  return useQuery<PerformanceBySymbol[]>({
    queryKey: ['performance', 'by-symbol'],
    queryFn: async () => {
      const data = await fetcher<Record<string, Omit<PerformanceBySymbol, 'symbol'>>>(
        '/api/v1/performance/by-symbol'
      );
      return Object.entries(data).map(([symbol, metrics]) => ({ symbol, ...metrics }));
    },
    staleTime: 10_000,
    refetchInterval: 30_000,
  });
}

export function usePaperTradingStatus() {
  return useQuery<PaperTradingStatus>({
    queryKey: ['paper-trading', 'status'],
    queryFn: () => fetcher('/api/v1/paper-trading/status'),
    staleTime: 10_000,
    refetchInterval: 30_000,
  });
}

export function usePaperTradingSignals(limit = 50) {
  return useQuery<Signal[]>({
    queryKey: ['paper-trading', 'signals', limit],
    queryFn: async () => {
      const data = await fetcher<{ signals: Signal[]; total: number }>(
        `/api/v1/paper-trading/signals?limit=${limit}`
      );
      return data.signals ?? [];
    },
    staleTime: 10_000,
    refetchInterval: 30_000,
  });
}

export function usePaperTradingTrades(limit = 50) {
  return useQuery<PaperTradeRecord[]>({
    queryKey: ['paper-trading', 'trades', limit],
    queryFn: async () => {
      const data = await fetcher<{ trades: PaperTradeRecord[]; total: number }>(
        `/api/v1/paper-trading/trades?limit=${limit}`
      );
      return data.trades ?? [];
    },
    staleTime: 10_000,
    refetchInterval: 30_000,
  });
}

export function useHealthCheck() {
  return useQuery<HealthStatus>({
    queryKey: ['health'],
    queryFn: () => fetcher('/health'),
    staleTime: 10_000,
    refetchInterval: 30_000,
    retry: 1,
  });
}

export function useReadyCheck() {
  return useQuery<ReadyStatus>({
    queryKey: ['ready'],
    queryFn: () => fetcher('/ready'),
    staleTime: 10_000,
    refetchInterval: 30_000,
    retry: 1,
  });
}

export function useOperatorStatus() {
  return useQuery<OperatorStatus>({
    queryKey: ['operator', 'status'],
    queryFn: () => fetcher('/api/v1/operator/status'),
    staleTime: 10_000,
    refetchInterval: 15_000,
    retry: 1,
  });
}

export function useEmergencyStopAction() {
  const invalidate = useInvalidateOperatorData();
  return useMutation<unknown, Error, string>({
    mutationFn: (reason: string) =>
      poster('/api/v1/operator/emergency-stop', { reason }),
    onSuccess: invalidate,
  });
}

export function useResumeTradingAction() {
  const invalidate = useInvalidateOperatorData();
  return useMutation<unknown, Error, string>({
    mutationFn: (reason: string) =>
      poster('/api/v1/operator/resume', { reason }),
    onSuccess: invalidate,
  });
}

export function useReconcileOrdersAction() {
  const invalidate = useInvalidateOperatorData();
  return useMutation<unknown, Error, void>({
    mutationFn: () => poster('/api/v1/system/reconcile'),
    onSuccess: invalidate,
  });
}

export function useCancelStaleOrdersAction() {
  const invalidate = useInvalidateOperatorData();
  return useMutation<unknown, Error, number | undefined>({
    mutationFn: (pricePctThreshold = 1.0) =>
      poster(`/api/v1/orders/stale/cancel?price_pct_threshold=${pricePctThreshold}`),
    onSuccess: invalidate,
  });
}

export function useResetPaperTradingAction() {
  const invalidate = useInvalidateOperatorData();
  return useMutation<unknown, Error, number | undefined>({
    mutationFn: (initialBalance?: number) =>
      poster('/api/v1/paper-trading/reset', { initial_balance: initialBalance }),
    onSuccess: invalidate,
  });
}
