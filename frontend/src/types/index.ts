export interface PortfolioSummary {
  total_value: number;
  total_pnl: number;
  positions_count: number;
  number_of_trades: number;
  source: string;
}

export interface Position {
  symbol: string;
  quantity: number;
  entry_price: number;
  current_price: number;
  pnl: number;
  pnl_percent: number;
}

export interface Trade {
  id?: number;
  symbol: string;
  side: string;
  quantity: number;
  price: number;
  timestamp: string;
  pnl?: number;
  status?: string;
}

export interface RiskStatus {
  emergency_stop: boolean;
  current_drawdown: number;
  daily_trades: number;
  max_daily_trades: number;
  max_drawdown_limit: number;
  risk_level?: string;
  [key: string]: unknown;
}

export interface TrailingStop {
  symbol: string;
  entry_price: number;
  current_price: number;
  stop_price: number;
  trail_percent: number;
  pnl?: number;
}

export interface MarketPrice {
  symbol: string;
  price: number;
  change_24h?: number;
  change_percent_24h?: number;
  timestamp?: string;
}

export interface SystemConfig {
  demo_mode: boolean;
  testnet: boolean;
  supported_symbols: string[];
  [key: string]: unknown;
}

export interface PerformanceSummary {
  win_rate: number;
  sharpe_ratio: number;
  max_drawdown: number;
  profit_factor: number;
  total_trades: number;
  total_pnl: number;
  [key: string]: unknown;
}

export interface PerformanceBySymbol {
  symbol: string;
  trades: number;
  win_rate: number;
  total_pnl: number;
  avg_pnl?: number;
}

export interface PaperTradingStatus {
  active: boolean;
  last_update: string;
  balance: number;
  total_pnl: number;
  win_rate: number;
  total_trades: number;
  [key: string]: unknown;
}

export interface Signal {
  id?: number;
  symbol: string;
  signal: string;
  confidence: number;
  timestamp: string;
  price?: number;
  [key: string]: unknown;
}

export interface HealthStatus {
  status: string;
  database?: string;
  schema?: string;
  [key: string]: unknown;
}

export interface ReadyStatus {
  ready: boolean;
  database?: boolean;
  binance_api?: boolean;
  cache?: boolean;
  [key: string]: unknown;
}
