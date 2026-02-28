import axios from 'axios';
import { useQuery } from '@tanstack/react-query';
import { API_BASE_URL } from '../config/api';
import type {
  PortfolioSummary,
  Position,
  Trade,
  RiskStatus,
  TrailingStop,
  MarketPrice,
  SystemConfig,
  PerformanceSummary,
  PerformanceBySymbol,
  PaperTradingStatus,
  Signal,
  HealthStatus,
  ReadyStatus,
} from '../types';

const api = axios.create({ baseURL: API_BASE_URL });

const fetcher = async <T>(url: string): Promise<T> => {
  const { data } = await api.get<T>(url);
  return data;
};

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
    queryFn: () => fetcher('/api/v1/portfolio/positions'),
    staleTime: 10_000,
    refetchInterval: 30_000,
  });
}

export function useTradeHistory(limit = 20) {
  return useQuery<Trade[]>({
    queryKey: ['portfolio', 'trade-history', limit],
    queryFn: () => fetcher(`/api/v1/portfolio/trade-history?limit=${limit}`),
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
  return useQuery<TrailingStop[]>({
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
    queryFn: () => fetcher(`/api/v1/performance/trades?limit=${limit}`),
    staleTime: 10_000,
    refetchInterval: 30_000,
  });
}

export function usePerformanceBySymbol() {
  return useQuery<PerformanceBySymbol[]>({
    queryKey: ['performance', 'by-symbol'],
    queryFn: () => fetcher('/api/v1/performance/by-symbol'),
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
    queryFn: () => fetcher(`/api/v1/paper-trading/signals?limit=${limit}`),
    staleTime: 10_000,
    refetchInterval: 30_000,
  });
}

export function usePaperTradingTrades(limit = 50) {
  return useQuery<Trade[]>({
    queryKey: ['paper-trading', 'trades', limit],
    queryFn: () => fetcher(`/api/v1/paper-trading/trades?limit=${limit}`),
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
