# GitHub Copilot Instructions – Binance Trading Agent

These instructions tell Copilot **how we want code and UI to be written** in this repo.

The project is a **Dash-based trading dashboard + FastAPI backend** for a Binance Testnet trading agent.

---

## 1. General Project Rules

- This project is **Binance Testnet only**.  
  - Never remove or bypass the `BINANCE_TESTNET` safety checks.
  - Do not add code that assumes mainnet trading or live money.

- Prefer **clear, maintainable code** over clever or extremely compact patterns.
  - Use type hints in Python functions.
  - Add short docstrings for public functions, especially in `agents/`, `api/`, and `dashboard/`.

- Do **not** introduce new third-party dependencies unless explicitly requested in a comment.
  - Use the existing stack: Python 3.10+, Dash, Plotly, Dash Bootstrap Components, FastAPI, SQLAlchemy.

- Keep **backwards compatibility** with existing behavior:
  - Reuse existing callback IDs, endpoint paths, and database schema.
  - If you must change an ID or path, add a `# TODO:` comment explaining why.

---

## 2. Architecture Overview (for Copilot)

When making suggestions, respect this structure:

- `binance_trade_agent/agents/…`
  - Trading agents: market data, signals, risk management, trade execution.
  - Stay focused on **business logic**, no UI code here.

- `binance_trade_agent/api/…`
  - FastAPI app and REST endpoints.
  - Use Pydantic models and FastAPI-style dependency injection.

- `binance_trade_agent/dashboard/…`
  - Dash app (main target for the UX/UI redesign).
  - Contains page modules such as:
    - `portfolio.py`
    - `market_data.py`
    - `signals.py`
    - `automation.py`
    - `execute_trade.py`
    - `system_health.py`
    - `logs.py`
    - `advanced.py`
  - Frontend styling lives in `binance_trade_agent/dashboard/assets/`.

- Database:
  - SQLite located in `data/`.
  - Accessed via SQLAlchemy models and queries. Do not add raw SQL unless clearly justified.

---

## 3. UI / UX Design Principles

When modifying anything under `binance_trade_agent/dashboard/`:

### 3.1 Visual Style

- **Dark, professional trading UI**, not flashy or neon.
- Use CSS classes and design tokens in `assets/` instead of inline styles.
- Assume a design system with:
  - Card components (`.ta-card`, `.ta-card--kpi`, etc.)
  - Layout helpers (`.ta-page`, `.ta-grid`, `.col-3`, `.col-4`, `.col-8`, `.col-12`, etc.)
  - Typography classes for headings, labels, KPI numbers.

If a class does not yet exist, suggest adding it to the shared CSS file in `assets/` rather than duplicating inline styles.

### 3.2 Layout & Hierarchy

Each dashboard page should:

1. Start with a clear **page header**:
   - Title, optional subtitle.
   - Optional “last updated” timestamp for live data.

2. Use a **grid layout** with reasonable max width:
   - Summary KPIs at the top.
   - Main charts/tables in the middle.
   - Detailed tables, logs, or configuration at the bottom.

3. Use a **small set of reusable patterns**:
   - **KPI row**: 3–4 cards showing key metrics (value + delta).
   - **Section card**: labeled container for charts/tables.
   - **Form card**: labeled inputs with primary and secondary actions.

Avoid deeply nested `html.Div`s with arbitrary margin/padding; prefer semantic sections and classes.

### 3.3 Behavior & Interactions

- Keep **interactions simple and explicit**:
  - Buttons should have clear labels (“Save Settings”, “Place Order”, “Start Agent”, “Stop Agent”).
  - Use tooltips for advanced metrics (drawdown, risk per trade, etc.).
  - Use alerts / toasts for success and error feedback, especially on:
    - Placing orders
    - Saving risk/strategy settings
    - Starting/stopping the trading agent

- When adding or editing callbacks:
  - Use descriptive IDs and component property names.
  - Avoid long monolithic callbacks; split when logic is unrelated.
  - Handle error cases explicitly and show friendly messages in the UI.

---

## 4. Page-Specific Guidance

### 4.1 Portfolio Page

**Goal:** Answer “How is my portfolio doing right now, and what just happened?”

When editing `dashboard/portfolio.py`:

- Put key KPIs in a **top row**:
  - Total Value
  - Total P&L (with %)
  - Open Positions
  - Total Trades
- Middle area:
  - Equity / P&L chart over time.
  - Portfolio allocation by symbol (pie/bar).
- Bottom:
  - Open positions table.
  - Recent trades table (last N trades, scrollable).

Use existing API endpoints for data; do not add new endpoints unless necessary.

### 4.2 Execute Trade Page

**Goal:** Answer “What exactly am I about to send to Binance, and is it safe?”

When editing `dashboard/execute_trade.py`:

- Left column: **Order form card**
  - Symbol selector, side (BUY/SELL), order type, price (if limit), quantity.
  - Optional SL/TP inputs in a clearly labeled section.
- Right column: **Market info & risk summary**
  - Current price & 24h change.
  - Estimated order value and position size as % of portfolio.
  - Risk status (“Within configured limits” vs “Exceeds max position 5%”).

Validate inputs and disable **Place Order** when the form is incomplete or violates risk settings.

### 4.3 Market Data Page

When editing `dashboard/market_data.py`:

- Header strip: symbol selector, timeframe, current price / 24h change.
- Main content:
  - Large candlestick chart with volume.
  - Order book depth or recent trades on the side.
- Secondary content: technical indicators (e.g., RSI) as smaller charts.

### 4.4 Signals & Risk Page

When editing `dashboard/signals.py`:

- Highlight **current signal** in a hero card (BUY/SELL/NEUTRAL + confidence %).
- Below: risk KPIs (current drawdown, max risk per trade, max position, portfolio value).
- Show **position limits** in a concise table with status pills (ACTIVE / DISABLED).

### 4.5 Automation Page

When editing `dashboard/automation.py`:

- Group content into logical cards:
  - Agent Status & Controls (start, stop, restart, current state).
  - Trading Settings (strategy, interval, symbols, quantity).
  - Risk Management (trade/hour, trade/day, max position, SL/TP).

Add toasts or inline messages when settings are applied.

### 4.6 System Health, Logs, Advanced

- **System Health**: high information density, small KPI tiles for uptime, error rates, and API connectivity.
- **Logs**: filter bar at the top; table with colored severity; optional modal/dialog for full log view.
- **Advanced**: group dangerous actions (e.g., Emergency Stop) in clearly marked, red-tinted sections with confirmation dialogs.

---

## 5. Coding Style for Python

- Use **PEP 8** for style and **flake8/black-friendly** formatting.
- Prefer this structure in new code:

```python
def some_function(arg1: str, arg2: int) -> ReturnType:
    """Short one-line summary.

    Longer explanation if needed.
    """
    ...
