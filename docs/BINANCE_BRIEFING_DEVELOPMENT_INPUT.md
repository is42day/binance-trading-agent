# Binance Briefing Development Input

This document translates `C:/Users/rautg/Downloads/Binance_Trading_Bot_Agent_Briefing.md` into concrete development input for this repository. It is written as an implementation handoff: each item names the current repo surface, the missing production behavior, and acceptance criteria for the next tranche of work.

## Current Repo Baseline

The project already covers several briefing requirements:

- REST Binance access through `binance_trade_agent/clients/binance_client.py`.
- Exchange filter validation through `get_symbol_rules()` and `validate_order_params()`.
- Order book slippage estimation through `estimate_market_order_slippage()`.
- FastAPI operator endpoints in `binance_trade_agent/api/api.py` for symbol rules, validation, slippage, risk status, trailing stops, and exchange reconciliation.
- Circuit breaker and retry behavior around Binance API calls.
- Local exchange order ledger and reconciliation through `binance_trade_agent/core/exchange_reconciliation.py`.
- Conservative risk caps in `binance_trade_agent/common/config.py`.
- Strategy validation tooling in `binance_trade_agent/scripts/micro_strategy_validator.py`.

The main production gaps are not "can it place a trade"; the project can. The gaps are operator safety, order lifecycle completeness, real-time data resilience, rate-limit observability, and strategy deployment discipline.

## Priority 0: Live-Safety Gate

Goal: prevent accidental live trading until the operator deliberately arms the system.

Current state:
- `BINANCE_TESTNET=true` is the default.
- `DEMO_MODE` is forced if keys are absent.
- The code warns when live mode is active, but live mode is still a configuration state rather than a deliberate arming flow.

Required change:
- Add a live-trading arming guard that requires all of:
  - `BINANCE_TESTNET=false`
  - `DEMO_MODE=false`
  - `LIVE_TRADING_ENABLED=true`
  - `LIVE_TRADING_ACK` equal to a fixed explicit phrase such as `I_ACCEPT_LIVE_BINANCE_SPOT_RISK`
- Refuse startup or order placement if any required live setting is missing.
- Expose the resolved mode in `/api/v1/system/config` without leaking secrets.

Acceptance criteria:
- Unit tests prove live trading is blocked unless all arming fields are set.
- Testnet and demo mode continue working without the live acknowledgement.
- Logs clearly say whether the runtime is `demo`, `testnet`, or `live_armed`.

Suggested prompt:

```text
Implement a live-trading arming gate. In Config, derive a runtime_mode value of demo, testnet, live_blocked, or live_armed. The execution client must refuse to create live Binance orders unless runtime_mode is live_armed. Add tests for missing keys, testnet, live without acknowledgement, and fully armed live mode. Do not log API secrets.
```

## Priority 1: Order Lifecycle Completeness

Goal: handle every Binance order status from the briefing instead of treating accepted orders as essentially complete.

Current state:
- `TradeExecutionAgent.place_order()` accepts `FILLED`, `PARTIALLY_FILLED`, and `NEW`.
- Filled quantity is booked immediately when present.
- Open orders can be reconciled later.
- There is no first-class OCO support.
- `get_order_status()` bypasses the wrapper and calls `self.client.client.get_order(...)` directly, which skips the client wrapper's retry and demo behavior.

Required change:
- Normalize all order statuses: `NEW`, `PARTIALLY_FILLED`, `FILLED`, `CANCELED`, `EXPIRED`, `REJECTED`.
- Add an `OrderLifecycleService` responsible for:
  - placing an order intent
  - recording exchange order acceptance
  - polling or reconciling until terminal state
  - booking only newly executed quantity
  - preserving partial-fill deltas
- Route `get_order_status()` through `BinanceAPIClient.get_order()`.
- Add cancellation and stale-order policy:
  - limit buy stale if price moves more than configured percent away
  - limit sell stale if price moves more than configured percent away
  - never cancel without recording a reason
- Add OCO execution support as a separate method, not a default path.

Acceptance criteria:
- Tests cover each order status and prove `PARTIALLY_FILLED` does not double-book fills across reconciliation runs.
- A `NEW` limit order remains tracked as open.
- `CANCELED`, `EXPIRED`, and `REJECTED` become terminal local states.
- The API can list open, terminal, and stale orders separately.

Suggested prompt:

```text
Create an order lifecycle layer around TradeExecutionAgent and ExchangeReconciliationService. Normalize Binance statuses, track partial-fill deltas, route status checks through BinanceAPIClient, and add stale limit-order detection. Add tests for NEW, PARTIALLY_FILLED, FILLED, CANCELED, EXPIRED, and REJECTED. Keep market orders supported, but prefer limit orders for strategy entries where price is supplied.
```

## Priority 2: WebSocket Market Data Service

Goal: stop relying only on repeated REST polling for active trading loops.

Current state:
- `MarketDataAgent` fetches prices, order books, and OHLCV via REST.
- Async cache paths exist, but sync paths currently bypass cache.
- There is no durable WebSocket stream manager for klines, trades, order book updates, or account/order updates.

Required change:
- Add `binance_trade_agent/core/market_streams.py` with:
  - kline stream subscriptions per symbol/interval
  - reconnect with exponential backoff and jitter
  - heartbeat tracking
  - bounded rolling candle buffers
  - stale-data detection
- Add a fallback rule:
  - Use websocket cache when fresh.
  - Fall back to REST only when stream data is missing or stale.
- Add stream health fields to `/api/v1/system/config` or a new `/api/v1/market/streams/status` endpoint.

Acceptance criteria:
- Stream manager can be tested with a fake message source.
- If no update arrives within `STREAM_STALE_SECONDS`, trading signal generation returns `HOLD` or fails closed.
- Reconnect attempts and last message timestamp are visible in the API/dashboard.

Suggested prompt:

```text
Implement a websocket market stream manager for Binance kline streams. It should maintain rolling OHLCV buffers by symbol and interval, reconnect with exponential backoff, expose stream health, and fail closed when data is stale. Integrate MarketDataAgent so strategies can consume fresh stream candles with REST fallback. Add unit tests using a fake async message source.
```

## Priority 3: Rate Limit Accounting

Goal: make Binance request weight visible and enforceable.

Current state:
- `429` responses back off and retry.
- The project does not track request weight budget, order request count, or `Retry-After` metadata centrally.

Required change:
- Add a `RateLimitTracker` in the Binance client layer.
- Track approximate weight per endpoint used by this app:
  - ticker price
  - order book depth
  - exchange info
  - klines
  - account balance
  - create/cancel/get order
- Record response headers when available.
- Pause trading when the local request budget is near threshold.
- Expose rate-limit state in the API and dashboard.

Acceptance criteria:
- Tests prove repeated API calls increment endpoint weights.
- A configured budget breach causes signal execution to skip order placement and log a blocked reason.
- `429` handling honors `Retry-After` if present.

Suggested prompt:

```text
Add Binance request-weight accounting to BinanceAPIClient. Track per-minute weight and order-call counts by endpoint, expose current usage through FastAPI, and block autonomous order placement when usage exceeds a configurable safety threshold. Enhance 429 handling to honor Retry-After. Add tests with fake Binance responses.
```

## Priority 4: Strategy Deployment Discipline

Goal: avoid promoting a strategy just because it trades frequently or looks good in a short test.

Current state:
- Multiple strategies exist: RSI, MACD, combined, Bollinger, edge, smart entry, combined edge.
- `buy_aggressive` produced trades in paper/testnet but also showed unacceptable drawdown in the reported run.
- `micro_strategy_validator.py` can validate strategy candidates against recent Binance klines.
- The safest current strategic direction is adaptive: trade only when a validated regime is present, otherwise stay flat.

Required change:
- Introduce a production candidate named `adaptive_core_micro`.
- Behavior:
  - Default signal is `HOLD`.
  - Long-term core component trades BTC/ETH only when higher-timeframe trend is positive.
  - Micro component trades only when recent validation for that symbol/interval is positive after fees and slippage.
  - Strategy output must include metadata explaining which component fired or why it held.
- Add a validation-gate artifact:
  - generated by `micro_strategy_validator.py`
  - stored as JSON under `data/strategy_validation/latest.json` or configurable path
  - consumed by the strategy or orchestrator
- Gate rules:
  - if validation missing: `HOLD`
  - if validation older than configured TTL: `HOLD`
  - if expected EUR/day <= 0 after fees/slippage: `HOLD`
  - if max drawdown exceeds threshold: `HOLD`

Acceptance criteria:
- Unit tests prove missing/stale/negative validation prevents trades.
- Backtest/validator command can produce the JSON gate file.
- Strategy metadata is visible in paper signal logs.
- `buy_aggressive` is explicitly marked testnet/paper-only in docs/config.

Suggested prompt:

```text
Implement an adaptive_core_micro production candidate. Add a strategy validation gate JSON artifact generated by the micro strategy validator. The strategy must default to HOLD unless higher-timeframe BTC/ETH trend is positive or the micro-grid validation gate is fresh and positive after fee/slippage assumptions. Include metadata for every HOLD/BUY/SELL decision and tests for missing, stale, negative, and positive validation gate states.
```

## Priority 5: Limit-First Execution Policy

Goal: reduce slippage and make entries auditable.

Current state:
- The trading loop executes default quantities through the orchestrator.
- Execution supports `MARKET` and `LIMIT`.
- Slippage estimation exists but is not yet a mandatory execution gate in autonomous trading.

Required change:
- Add an execution policy object:
  - `execution_mode`: `market`, `limit`, or `maker_first`
  - `max_spread_pct`
  - `max_slippage_pct`
  - `limit_price_offset_bps`
  - `stale_order_seconds`
- Before order placement:
  - validate exchange filters
  - fetch depth
  - calculate spread and slippage
  - reject if spread or slippage is too high
  - prefer limit order when configured
- Record rejection reason in decision metadata.

Acceptance criteria:
- Tests prove wide spread blocks entry.
- Tests prove slippage above threshold blocks market order.
- Limit order price is rounded to tick size and quantity to step size.
- Paper logs show `execution_policy`, `spread_pct`, `slippage_pct`, and `blocked_reason`.

Suggested prompt:

```text
Add an autonomous execution policy layer before TradeExecutionAgent.place_order. It must validate filters, calculate spread/slippage from order book depth, support maker_first limit entries, block orders above max spread/slippage, and record detailed decision metadata. Add tests for blocked spread, blocked slippage, rounded limit price, and successful limit-first placement.
```

## Priority 6: Operator Dashboard Fields

Goal: make the dashboard useful for supervising autonomous trading on a VPS.

Current state:
- FastAPI exposes health, risk, portfolio, performance, paper trading, validation, slippage, and exchange orders.
- React dashboard shows modern system health, but not all production-critical Binance fields are necessarily surfaced.

Required dashboard additions:
- Runtime mode: `demo`, `testnet`, `live_blocked`, `live_armed`.
- Binance circuit breaker state.
- Rate-limit usage.
- Stream freshness by symbol/interval.
- Last strategy validation gate timestamp/result.
- Current execution policy.
- Open exchange orders by status and stale flag.
- Last blocked trade reason.
- Emergency stop state and reason.

Acceptance criteria:
- Dashboard can answer: "Is the bot armed?", "Is data fresh?", "Why did it not trade?", "Are there stuck orders?", and "Are we near Binance limits?"

Suggested prompt:

```text
Extend the React dashboard and FastAPI APIs to show runtime mode, stream freshness, rate-limit usage, strategy gate status, execution policy, stale open orders, last blocked trade reason, and emergency stop state. Keep secrets hidden. Add frontend types and API hook updates.
```

## Priority 7: Agent Prompt API Contracts

Goal: turn vague operator prompts into safe, structured workflows.

Add or document these API-level contracts:

### Validate order

Input:

```json
{
  "symbol": "BTCUSDT",
  "side": "BUY",
  "order_type": "LIMIT",
  "quantity": 0.001,
  "price": 50000
}
```

Output:

```json
{
  "valid": true,
  "errors": [],
  "warnings": [],
  "normalized_quantity": 0.001,
  "normalized_price": 50000.0,
  "notional": 50.0
}
```

### Estimate slippage

Input:

```json
{
  "symbol": "BTCUSDT",
  "side": "BUY",
  "quantity": 0.5,
  "depth_limit": 50
}
```

Output:

```json
{
  "effective_price": 80210.15,
  "mid_price": 80200.00,
  "slippage_pct": 0.0127,
  "levels_consumed": 3,
  "unfilled_quantity": 0.0
}
```

### Explain last decision

Required new endpoint:

```text
GET /api/v1/trading/decisions/latest?symbol=BTCUSDT
```

Output should include:

```json
{
  "symbol": "BTCUSDT",
  "signal": "HOLD",
  "strategy": "adaptive_core_micro",
  "confidence": 0.0,
  "blocked_reason": "strategy_validation_gate_negative",
  "risk_approved": false,
  "execution_policy": {
    "mode": "maker_first",
    "max_spread_pct": 0.05,
    "max_slippage_pct": 0.10
  },
  "timestamp": "2026-05-10T12:00:00Z"
}
```

## Recommended Next Implementation Order

1. Live-safety gate.
2. Decision journal / latest decision endpoint.
3. Execution policy with mandatory spread and slippage checks.
4. Strategy validation gate artifact.
5. `adaptive_core_micro` production candidate.
6. WebSocket kline stream manager.
7. Rate-limit tracker and dashboard surfacing.
8. OCO and stale-order lifecycle enhancements.

This order gives the project a safer operator loop before adding more autonomous trading intelligence.

## Production Readiness Definition

Do not call the bot production ready until all of these are true:

- Live trading requires explicit arming.
- No strategy can trade without fresh market data.
- No autonomous order can bypass exchange filter validation.
- Market orders are blocked by spread/slippage policy unless explicitly allowed.
- Partial fills are reconciled without double booking.
- Open orders are monitored for stale state.
- Binance 429/rate-limit state is visible and blocks new orders near threshold.
- Dashboard explains every recent trade and non-trade.
- The promoted production strategy is validated over multiple lookback windows and can go flat.
- Testnet and paper tests pass after a clean state reset.

