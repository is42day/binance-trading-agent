export interface PortfolioSummary {
  total_value: number;
  total_pnl: number;
  positions_count: number;
  number_of_trades: number;
  win_rate?: number;
  max_drawdown?: number;
  source?: string;
}

export interface Position {
  symbol: string;
  side: string;
  quantity: number;
  average_price: number;
  current_price: number;
  unrealized_pnl: number;
  realized_pnl: number;
  market_value: number;
  total_pnl: number;
  timestamp?: string;
}

export interface Trade {
  trade_id?: string;
  symbol: string;
  side: string;
  quantity: number;
  price: number;
  fee?: number;
  timestamp: string;
  pnl?: number;
  total_value?: number;
  order_id?: string;
}

export interface RiskStatus {
  emergency_stop: boolean;
  current_drawdown: number;
  daily_trades: number;
  consecutive_losses?: number;
  risk_rules_active?: number;
  trailing_stops_active?: number;
  source?: string;
  [key: string]: unknown;
}

export interface TrailingStopEntry {
  entry_price: number;
  side: string;
  highest_price?: number;
  lowest_price?: number;
  current_stop: number;
  trailing_pct: number;
  registered_at?: string;
}

export interface TrailingStopsResponse {
  active_stops: number;
  positions: Record<string, TrailingStopEntry>;
}

export interface MarketPrice {
  symbol: string;
  price: number;
  source?: string;
}

export interface SystemConfig {
  demo_mode: boolean;
  binance_testnet: boolean;
  supported_symbols: string[];
  risk_config?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface PerformanceSummary {
  win_rate: number;
  sharpe_ratio: number;
  max_drawdown: number;
  max_drawdown_pct?: number;
  profit_factor: number;
  total_trades: number;
  closed_trades?: number;
  total_pnl: number;
  total_return_pct?: number;
  initial_capital?: number;
  current_capital?: number;
  [key: string]: unknown;
}

export interface PerformanceBySymbol {
  symbol: string;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  total_pnl: number;
  avg_pnl: number;
}

export interface PaperPortfolio {
  current_balance: number;
  total_pnl: number;
  total_pnl_percent: number;
  win_rate: number;
  total_trades: number;
  max_drawdown: number;
  open_positions: number;
  profit_factor: number;
}

export interface PaperTradingStatus {
  active: boolean;
  last_update?: string;
  age_seconds?: number;
  portfolio: PaperPortfolio | null;
  signals_count?: number;
  message?: string;
}

export interface Signal {
  symbol?: string;
  signal?: string;
  action?: string;
  confidence?: number;
  timestamp?: string;
  price?: number;
  [key: string]: unknown;
}

export interface HealthStatus {
  status: string;
  timestamp?: string;
  checks?: {
    database?: string;
    schema?: string;
  };
  [key: string]: unknown;
}

export interface ReadyStatus {
  ready: boolean;
  timestamp?: string;
  checks?: {
    database?: string;
    binance_api?: string;
    cache?: string;
  };
}
