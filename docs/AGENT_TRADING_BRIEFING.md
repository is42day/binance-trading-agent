# Agent Trading Briefing

This project exposes a conservative API surface for AI-assisted trading workflows. Agent prompts should resolve into explicit data reads, validation, and execution steps instead of jumping directly to an order.

## Pre-Trade Controls

Before any live or testnet order, call the validation and slippage endpoints:

- `GET /api/v1/market/symbol-rules/{symbol}` returns Binance exchange filters such as tick size, quantity step size, and minimum notional.
- `GET /api/v1/market/order-validation?symbol=BTCUSDT&side=BUY&order_type=LIMIT&quantity=0.001&price=50000` validates and normalizes quantity and price before order placement.
- `GET /api/v1/market/slippage?symbol=BTCUSDT&side=BUY&quantity=0.5&limit=50` estimates market-order effective price, unfilled quantity, consumed levels, and slippage from order book depth.

The execution client also validates orders internally, so direct execution calls receive the same Binance filter guardrails.

## Prompt Patterns

Use prompts that specify intent, constraints, and expected output:

- "Validate a BTCUSDT limit buy for 0.001 BTC at 50000 USDT. Return JSON with valid, errors, normalized_quantity, normalized_price, and notional."
- "Estimate slippage for market buying 0.5, 1, and 2 BTC on BTCUSDT. Do not place orders."
- "Only place a limit order if validation passes and estimated slippage is below 0.25%. Otherwise return the blocking reason."

## Execution Guardrails

Autonomous execution should keep these defaults:

- Never log API secrets.
- Treat `HOLD` as non-actionable.
- Validate exchange filters before placing orders.
- Reconcile partially filled and open exchange orders.
- Back off on Binance `429` rate-limit responses.
- Prefer testnet or paper trading until the deployed VPS stack is verified from the current `main` image.

## Useful Output Shape

For agent-readable responses, prefer:

```json
{
  "symbol": "BTCUSDT",
  "action": "validate_order",
  "valid": true,
  "errors": [],
  "warnings": [],
  "normalized_quantity": 0.001,
  "normalized_price": 50000.0,
  "notional": 50.0
}
```
