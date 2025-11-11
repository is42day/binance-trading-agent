# Streamlit → Plotly Dash Migration Plan

**Status**: Starting Phase 1  
**Timeline**: 2-3 days  
**Scope**: Complete UI/UX redesign, all pages migrated

---

## Executive Summary

We're migrating from Streamlit to Plotly Dash to:
- ✅ Get **full CSS/styling control** (no more fighting the framework)
- ✅ Create **professional financial dashboard** (Dash is built for this)
- ✅ Enable **responsive design** (works on mobile/tablet/desktop)
- ✅ Maintain **all backend logic** (Python agents stay unchanged)
- ✅ Keep **Docker deployment** (minimal infrastructure changes)

---

## Migration Phases

### Phase 1: Analysis & Inventory ⚡ CURRENT
**Objective**: Document current Streamlit structure

**Current Streamlit Pages:**
1. Portfolio - balance, P&L, positions table, allocation pie chart
2. Market Data - price ticker, candlestick chart, order book, technical indicators
3. Signals & Risk - signal display, risk metrics, confidence scores
4. Execute Trade - trade form, order execution, recent trades table
5. System Health - system status, health metrics, emergency controls
6. Logs - system logging, monitoring
7. Advanced - system controls, configuration, export/restart

**Data Sources:**
- `get_portfolio_data()` - Portfolio stats, positions, trades
- `get_market_data(symbol)` - Price, 24h ticker
- `get_ohlcv_data(symbol)` - Candlestick data
- `get_signals()` - Trading signals
- `get_risk_status()` - Risk metrics
- `get_system_status()` - System health

**Components to Port:**
- Metric cards (Portfolio Value, P&L, Risk Status, etc)
- Tables (positions, trades)
- Charts (pie chart, candlestick, line charts)
- Forms (trade execution, settings)
- Real-time updates (auto-refresh capability)

---

### Phase 2: Project Setup
**Objective**: Create Dash project structure

**Files to Create:**
```
dash_app/
├── app.py                 # Main Dash app
├── requirements.txt       # Dependencies
├── assets/
│   ├── style.css         # Custom CSS
│   └── logo.png          # Trading Agent logo
├── pages/
│   ├── portfolio.py      # Portfolio page
│   ├── market_data.py    # Market data page
│   ├── signals_risk.py   # Signals & Risk page
│   ├── execute_trade.py  # Trade execution page
│   ├── system_health.py  # System health page
│   ├── logs.py           # Logs page
│   └── advanced.py       # Advanced controls page
├── components/
│   ├── navbar.py         # Navigation bar
│   ├── metric_card.py    # Metric card component
│   ├── tables.py         # Table components
│   └── charts.py         # Chart components
└── utils/
    ├── data_fetch.py     # Data fetching functions
    └── callbacks.py      # Shared callbacks
```

**Dependencies (requirements.txt):**
```
dash==2.14.0
plotly==5.18.0
dash-bootstrap-components==1.5.0
pandas==2.0.0
requests==2.31.0
```

---

### Phase 3: Dash Foundation
**Objective**: Build core app structure with navigation

**Key Components:**
- Multi-page navigation (using dcc.Location)
- Responsive Bootstrap layout
- Theme configuration (dark mode, orange accents)
- Tab/page routing system

**Code Structure:**
```python
# app.py
from dash import Dash, html, dcc
import dash_bootstrap_components as dbc

app = Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])

app.layout = dbc.Container([
    dcc.Location(id='url', refresh=False),
    dbc.NavbarSimple([...]),  # Navigation
    dbc.Container(id='page-content'),  # Page content
], fluid=True)

@app.callback(Output('page-content', 'children'),
              Input('url', 'pathname'))
def display_page(pathname):
    if pathname == '/portfolio':
        return portfolio.layout
    # ... more pages
```

---

### Phase 4: Backend Integration
**Objective**: Connect Dash to trading agents

**Data Fetching Pattern:**
```python
# utils/data_fetch.py
def get_portfolio():
    # Call existing portfolio manager
    # Return formatted dict for Dash
    
def get_market_data(symbol):
    # Call existing market agent
    # Return formatted data

# pages/portfolio.py
@app.callback(
    Output('portfolio-metrics', 'children'),
    Input('refresh-interval', 'n_intervals')
)
def update_portfolio(n):
    data = data_fetch.get_portfolio()
    return create_metric_cards(data)
```

**Reuse existing functions:**
- `get_portfolio_data()` 
- `get_market_data(symbol)`
- `get_signals()`
- `get_risk_status()`
- etc.

---

### Phase 5: Portfolio Page
**Layout:**
```
┌─────────────────────────────────────────┐
│ Portfolio Overview                      │
├────────┬────────┬────────┬────────┐
│ Total  │ Total  │ Open   │ Total  │
│ Value  │ P&L    │ Pos    │ Trades │
├────────┴────────┴────────┴────────┤
│                                     │
│  Asset Distribution Pie Chart       │
│                                     │
├─────────────────────────────────────┤
│ Position Sizes Bar Chart            │
├─────────────────────────────────────┤
│ Current Positions Table             │
├─────────────────────────────────────┤
│ Recent Trades Table                 │
└─────────────────────────────────────┘
```

**Components:**
- 4 metric cards (using custom component)
- Plotly pie chart (asset distribution)
- Plotly bar chart (position sizes)
- dbc.Table for positions
- dbc.Table for trades
- Color coding (green/red for P&L)

---

### Phase 6: Market Data Page
**Layout:**
```
┌─────────────────────────────────────────┐
│ Market Data - BTCUSDT                   │
│ [Symbol Selector] [Timeframe] [Hours]   │
├────────┬────────┬────────┬────────┐
│ Price  │ 24h    │ 24h    │ 24h    │
│        │ High   │ Low    │ Change │
├─────────────────────────────────────────┤
│                                         │
│  Candlestick Chart (Plotly)             │
│                                         │
├─────────────────────────────────────────┤
│  Volume Bar Chart                       │
├─────────────────────────────────────────┤
│  Technical Indicators: RSI, SMA         │
├────────┬────────┬────────┐
│ RSI    │ Price  │ Volume │
│ Value  │ vs SMA │ Status │
├─────────────────────────────────────────┤
│  Order Book (Bids/Asks)                 │
└─────────────────────────────────────────┘
```

---

### Phase 7: Signals & Risk + System Health Pages
**Signals & Risk Page:**
- Trading signal display (BUY/SELL/HOLD)
- Confidence score
- Risk status with emergency stop button
- Risk metrics (drawdown, consecutive losses)

**System Health Page:**
- 3 metric cards (Trading Mode, API Status, System Status)
- 4 metric cards (Portfolio Health, Risk Status, Signal Confidence, Active Positions)
- Emergency controls section
- Trading mode configuration

---

### Phase 8: Trade Execution & Logs Pages
**Execute Trade Page:**
- Trade form (symbol, side, quantity)
- Current price display
- Order confirmation
- Recent trades table

**Logs Page:**
- System health status
- Performance metrics
- Log viewer
- System information

---

### Phase 9: Advanced Page & Styling
**Advanced Page:**
- Emergency stop button
- Resume trading button
- Export portfolio data
- Restart orchestrator
- Refresh strategy
- System information

**CSS Styling:**
- Dark theme (dark gray backgrounds)
- Orange accents (#ff914d) for borders/highlights
- Professional spacing and typography
- Responsive grid layout
- Metric cards with left border accent
- Hover effects on interactive elements

---

### Phase 10: QA & Testing
**Test Coverage:**
- ✅ All pages render correctly
- ✅ All data fetching works
- ✅ Real-time updates work
- ✅ Forms submit correctly
- ✅ Charts render properly
- ✅ Responsive on mobile (375px)
- ✅ Responsive on tablet (768px, 1024px)
- ✅ Responsive on desktop (1440px, 1920px)
- ✅ Cross-browser (Chrome, Firefox, Safari, Edge)

**Create Documentation:**
- Before/After screenshots
- User guide
- API integration notes

---

### Phase 11: Deployment
**Docker Changes:**
- Replace Streamlit with Dash in supervisord.conf
- Update port (keep 8501 or switch to standard port 8050)
- Update requirements.txt

**Git:**
- Create `feature/dash-migration` branch
- Commit work regularly
- Final merge to main

---

## Architecture Comparison

### Streamlit (OLD)
```
User → Browser → Streamlit Server
                    ↓
                Pages (*.py)
                    ↓
                Trading Agents
                    ↓
                Binance API
```

### Dash (NEW)
```
User → Browser → Dash Server (Flask-based)
                    ↓
                Callbacks/Pages
                    ↓
                Data Fetching Layer
                    ↓
                Trading Agents
                    ↓
                Binance API
```

**Key difference**: Dash uses standard web callbacks, giving us full control over rendering.

---

## Development Environment

**Current Setup We're Keeping:**
- ✅ Docker container
- ✅ Trading agents (market_agent, signal_agent, etc)
- ✅ Portfolio manager
- ✅ Risk management
- ✅ Binance API connection
- ✅ MCP server

**What's Changing:**
- ❌ Streamlit (→ Dash)
- ✅ Python backend (stays same)
- ✅ Data layer (stays same)
- ❌ web_ui.py (→ dash app/)

---

## Success Criteria

✅ All pages functional and accessible  
✅ Data displays correctly (no alignment issues)  
✅ Charts render properly with Plotly  
✅ Forms work (trade execution, settings)  
✅ Responsive design works  
✅ Professional appearance (orange/dark theme)  
✅ No CSS fighting or styling issues  
✅ Performance acceptable (< 2s page load)  
✅ All existing trading logic preserved  

---

## Estimated Timeline

| Phase | Task | Time |
|-------|------|------|
| 1 | Analyze structure | 30 min |
| 2 | Setup project | 30 min |
| 3 | Build foundation | 1 hour |
| 4 | Backend integration | 1 hour |
| 5-9 | Build all pages | 4-6 hours |
| 10 | QA & testing | 2 hours |
| 11 | Deploy | 30 min |
| **Total** | | **2-3 days** |

---

## Next Steps

1. ✅ Approve migration plan (you just did!)
2. 🔄 Start Phase 1: Analyze current structure
3. Create Dash project structure (Phase 2)
4. Build and test incrementally

Ready to start Phase 1?
