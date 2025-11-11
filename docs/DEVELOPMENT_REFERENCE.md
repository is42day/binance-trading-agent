# Binance Trading Agent - Development Reference

Advanced documentation for contributors, maintainers, and developers implementing new features or optimizing the system.

**Table of Contents:**
- [Development Environment Setup](#development-environment-setup)
- [Architecture Patterns](#architecture-patterns)
- [API Reference](#api-reference)
- [Testing Strategies](#testing-strategies)
- [Performance & Optimization](#performance--optimization)
- [Extending the System](#extending-the-system)
- [Common Gotchas](#common-gotchas)
- [Debugging & Logging](#debugging--logging)

---

## Development Environment Setup

### Local Development Setup

**Prerequisites:**
- Python 3.10+ (exact version matters for async compatibility)
- Git for version control
- Docker & Docker Compose (recommended)
- IDE: VS Code with Python extension recommended

**Installation Steps:**

```bash
# 1. Clone repository
git clone https://github.com/is42day/binance-trading-agent.git
cd binance-trading-agent

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install in editable mode with dev dependencies
pip install -e ".[dev]"
# Or: pip install -r requirements.txt

# 4. Setup pre-commit hooks (optional but recommended)
pip install pre-commit
pre-commit install

# 5. Configure IDE for formatting
# Install Black, isort, flake8 in virtual environment
pip install black isort flake8 pylint
```

### VS Code Settings (`.vscode/settings.json`)

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.formatting.provider": "black",
  "[python]": {
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  },
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": [
    "binance_trade_agent/tests",
    "-v"
  ]
}
```

### Docker Development Setup

**Advantages Over Local:**
- Consistent environment across team
- Easy database/cache reset
- No Python version conflicts
- Matches production environment

**Setup:**

```bash
# 1. Build development image with hot reload
docker-compose build

# 2. Start with volume mounts for live editing
docker-compose up -d

# 3. Code changes immediately reflected in container
# (Edit files locally, container sees changes)

# 4. Run tests in container
docker-compose exec trading-agent pytest -v

# 5. Access Python shell in container
docker-compose exec trading-agent python
```

---

## Architecture Patterns

### Agent Communication Pattern

Each agent communicates via standardized interfaces (dictionaries), not direct method calls:

```python
# ✅ CORRECT - Using standard interfaces
signal_result = {
    'signal': 'BUY',
    'confidence': 0.85,
    'indicators': {
        'rsi': 35,
        'macd': 0.15,
        'timestamp': datetime.now()
    }
}

risk_result = risk_agent.validate_trade(
    symbol='BTCUSDT',
    side='BUY',
    quantity=0.1,
    price=43000
)
# Returns: {'approved': True, 'reason': '...', 'recommended_quantity': 0.1}

# ❌ WRONG - Direct method calls create tight coupling
signal_agent.execute_trade(risk_agent, portfolio_manager)
```

### Error Handling Pattern

All agent operations must include correlation logging:

```python
import logging
from datetime import datetime

class MyAgent:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def operation(self, params):
        correlation_id = f"op_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        extra = {'correlation_id': correlation_id}
        
        try:
            self.logger.info(f"Starting operation with {params}", extra=extra)
            result = await self._do_work(params)
            self.logger.info("Operation succeeded", extra=extra)
            return result
        
        except ValueError as e:
            self.logger.warning(f"Validation error: {str(e)}", extra=extra)
            raise
        
        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}", extra=extra)
            raise
```

### Type Flexibility Pattern

Handle both ORM objects and dictionaries for robustness:

```python
class PortfolioManager:
    def record_trade(self, trade):
        """Accept both TradeORM objects and dictionaries"""
        
        # Handle dict
        if isinstance(trade, dict):
            symbol = trade.get('symbol')
            side = trade.get('side')
            quantity = trade.get('quantity')
            price = trade.get('price')
            fee = trade.get('fee', 0)
        
        # Handle ORM object
        elif hasattr(trade, 'symbol'):
            symbol = trade.symbol
            side = trade.side
            quantity = trade.quantity
            price = trade.price
            fee = trade.fee or 0
        
        else:
            raise TypeError(f"Unsupported trade type: {type(trade)}")
        
        # Validate required fields
        if not all([symbol, side, quantity, price]):
            raise ValueError(f"Trade missing required fields")
        
        # Process trade
        self._store_position(symbol, side, quantity, price, fee)
```

### Async Optimization Pattern

For high-performance concurrent operations:

```python
import asyncio
from aiohttp import ClientSession

class AsyncMarketDataAgent:
    def __init__(self):
        self.session = None
    
    async def __aenter__(self):
        self.session = ClientSession()
        return self
    
    async def __aexit__(self, *args):
        await self.session.close()
    
    async def fetch_prices_batch(self, symbols):
        """Fetch multiple prices concurrently"""
        tasks = [
            self._fetch_single_price(symbol)
            for symbol in symbols
        ]
        return await asyncio.gather(*tasks)
    
    async def _fetch_single_price(self, symbol):
        # Network I/O - concurrent with other requests
        async with self.session.get(f'https://api.binance.com/price?symbol={symbol}') as resp:
            return await resp.json()

# Usage - all 3 prices fetched concurrently, not sequentially
async def main():
    async with AsyncMarketDataAgent() as agent:
        prices = await agent.fetch_prices_batch(['BTCUSDT', 'ETHUSDT', 'BNBUSDT'])
        # Takes ~1 second instead of 3 seconds
```

### Database Connection Pattern

Using SQLAlchemy for ORM operations:

```python
from sqlalchemy import create_engine, Column, String, Float, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

class TradeORM(Base):
    __tablename__ = 'trades'
    trade_id = Column(String, primary_key=True)
    symbol = Column(String, nullable=False)
    side = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    created_at = Column(DateTime, nullable=False)

class PortfolioManager:
    def __init__(self, db_path):
        self.engine = create_engine(f'sqlite:///{db_path}')
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
    
    def record_trade(self, trade_data):
        session = self.Session()
        try:
            trade_orm = TradeORM(**trade_data)
            session.add(trade_orm)
            session.commit()
        finally:
            session.close()
```

---

## API Reference

### MarketDataAgent

**Fetch Current Price:**
```python
agent = MarketDataAgent()
data = agent.fetch_data('BTCUSDT')
# Returns:
# {
#     'symbol': 'BTCUSDT',
#     'open': 43100.00,
#     'high': 43500.00,
#     'low': 42800.00,
#     'close': 43200.00,
#     'volume': 1234567.89,
#     'timestamp': datetime(2025, 11, 9, 12, 0, 0)
# }
```

**Batch Price Fetching (Async):**
```python
async with AsyncMarketDataAgent() as agent:
    prices = await agent.fetch_prices_batch([
        'BTCUSDT', 'ETHUSDT', 'BNBUSDT'
    ])
    # Fetches 3 prices concurrently
```

**Indicators Calculation:**
```python
indicators = agent.calculate_indicators(symbol='BTCUSDT', period=14)
# Returns:
# {
#     'rsi': 65.5,           # RSI(14)
#     'macd': 0.15,          # MACD line
#     'macd_signal': 0.12,   # MACD signal
#     'macd_histogram': 0.03,
#     'bb_upper': 43500,     # Bollinger Bands
#     'bb_middle': 43000,
#     'bb_lower': 42500
# }
```

### SignalAgent

**Generate Trading Signal:**
```python
agent = SignalAgent(market_data_agent)
signal = agent.analyze(market_data, strategy='RSI')
# Returns:
# {
#     'signal': 'BUY',              # 'BUY', 'SELL', 'HOLD'
#     'confidence': 0.78,            # 0.0 to 1.0
#     'indicators': {
#         'rsi_value': 35,
#         'rsi_level': 'OVERSOLD',
#         'timestamp': datetime(...)
#     },
#     'strategy': 'RSI'
# }
```

**Strategy Options:**
- `'RSI'` - Relative Strength Index (momentum)
- `'MACD'` - Moving Average Convergence Divergence
- `'BB'` - Bollinger Bands (volatility)
- `'COMBINED'` - Weighted average of all strategies

### RiskManagementAgent

**Validate Trade:**
```python
result = agent.validate_trade(
    symbol='BTCUSDT',
    side='BUY',
    quantity=0.1,
    price=43000
)
# Returns:
# {
#     'approved': True,
#     'reason': 'Within position limits',
#     'recommended_quantity': 0.05  # Adjusted if needed
# }
```

**Get Risk Metrics:**
```python
metrics = agent.get_risk_metrics()
# Returns:
# {
#     'total_exposure': 0.23,        # 23% of portfolio
#     'portfolio_heat': 0.18,        # 18% max allowed
#     'emergency_stop_active': False,
#     'risk_score': 35,              # 0-100
#     'warning_level': 'SAFE'        # SAFE, WARNING, CRITICAL
# }
```

**Emergency Stop Control:**
```python
agent.activate_emergency_stop()     # Halt all trading
agent.deactivate_emergency_stop()   # Resume trading
status = agent.is_emergency_stop_active()  # Check status
```

### TradeExecutionAgent

**Place Order:**
```python
order = agent.place_order(
    symbol='BTCUSDT',
    side='BUY',
    order_type='LIMIT',
    quantity=0.1,
    price=43000
)
# Returns:
# {
#     'order_id': 'ord_1234567',
#     'symbol': 'BTCUSDT',
#     'side': 'BUY',
#     'status': 'NEW',
#     'quantity': 0.1,
#     'price': 43000
# }
```

**Get Order Status:**
```python
status = agent.get_order_status(order_id='ord_1234567')
# Returns: 'NEW', 'PARTIALLY_FILLED', 'FILLED', 'CANCELLED', 'EXPIRED'
```

**Cancel Order:**
```python
agent.cancel_order(order_id='ord_1234567')
# Returns: True if successful
```

### PortfolioManager

**Record Trade:**
```python
pm.record_trade({
    'symbol': 'BTCUSDT',
    'side': 'BUY',
    'quantity': 0.1,
    'price': 43000,
    'fee': 5.00,
    'timestamp': datetime.now()
})
```

**Get Portfolio Stats:**
```python
stats = pm.get_portfolio_stats()
# Returns:
# {
#     'total_value': 10500.00,
#     'total_pnl': 150.00,
#     'pnl_percent': 1.44,
#     'number_of_trades': 5,
#     'positions_count': 3
# }
```

**Get All Positions:**
```python
positions = pm.get_all_positions()
# Returns list of:
# {
#     'symbol': 'BTCUSDT',
#     'quantity': 0.1,
#     'average_price': 42500,
#     'current_price': 43200,
#     'unrealized_pnl': 70.00,
#     'position_value': 4320.00
# }
```

**Get Trade History:**
```python
trades = pm.get_trade_history(limit=10)
# Returns list of:
# {
#     'trade_id': 'web_1234567890',
#     'symbol': 'BTCUSDT',
#     'side': 'BUY',
#     'quantity': 0.1,
#     'price': 43000,
#     'fee': 5.00,
#     'timestamp': datetime(...),
#     'pnl': 70.00  # For closed positions
# }
```

### MCP Tools

**Tool Format:**
```python
# Input
{
    "type": "tool_call",
    "name": "get_price",
    "input": {
        "symbol": "BTCUSDT"
    }
}

# Output
{
    "type": "tool_result",
    "content": {
        "symbol": "BTCUSDT",
        "price": 43200.00,
        "timestamp": "2025-11-09T12:00:00Z"
    }
}
```

**Available Tools:**

| Tool | Input | Output |
|------|-------|--------|
| `get_price` | `symbol` | `{price, timestamp}` |
| `get_indicators` | `symbol, period` | `{rsi, macd, bb_*}` |
| `place_order` | `symbol, side, quantity, price` | `{order_id, status}` |
| `cancel_order` | `order_id` | `{success, reason}` |
| `get_open_orders` | `symbol` | `[{order_id, ...}]` |
| `get_portfolio_stats` | none | `{total_value, pnl, ...}` |
| `get_positions` | none | `[{symbol, quantity, ...}]` |
| `get_trades` | `limit, offset` | `[{trade_id, symbol, ...}]` |
| `check_position_size` | `symbol, quantity` | `{approved, reason}` |
| `analyze_signal` | `symbol, strategy` | `{signal, confidence, ...}` |
| `emergency_stop` | `action` | `{success, status}` |

---

## Testing Strategies

### Unit Testing Pattern

**Structure:**
```python
import pytest
from unittest.mock import Mock, patch, MagicMock

class TestMarketDataAgent:
    @pytest.fixture
    def agent(self):
        """Setup agent with mocked dependencies"""
        return MarketDataAgent()
    
    @pytest.fixture
    def mock_price_response(self):
        """Mock Binance API response"""
        return {
            'symbol': 'BTCUSDT',
            'close': '43200.00',
            'volume': '1234567.89'
        }
    
    def test_fetch_data_returns_dict(self, agent, mock_price_response):
        """Verify return type is dictionary"""
        with patch('binance_trade_agent.market_data_agent.fetch_price',
                   return_value=mock_price_response):
            result = agent.fetch_data('BTCUSDT')
            
            assert isinstance(result, dict)
            assert result['symbol'] == 'BTCUSDT'
            assert result['close'] == 43200.00
    
    def test_calculate_indicators_returns_all_fields(self, agent):
        """Verify all indicators are calculated"""
        prices = [100 + i for i in range(50)]  # 50-day price history
        indicators = agent.calculate_indicators_from_prices(prices)
        
        assert 'rsi' in indicators
        assert 'macd' in indicators
        assert 'bb_upper' in indicators
        assert all(isinstance(v, (int, float)) for v in indicators.values())
```

### Integration Testing Pattern

**End-to-End Workflow Test:**
```python
@pytest.mark.integration
class TestTradingWorkflow:
    def test_complete_buy_workflow(self):
        """Test complete workflow: market data → signal → risk → execution"""
        
        # Setup
        market_data = MarketDataAgent()
        signals = SignalAgent(market_data)
        risk = RiskManagementAgent()
        execution = TradeExecutionAgent()
        portfolio = PortfolioManager(':memory:')  # In-memory DB for testing
        
        # 1. Fetch market data
        data = market_data.fetch_data('BTCUSDT')
        assert data['symbol'] == 'BTCUSDT'
        
        # 2. Generate signal
        signal = signals.analyze(data, strategy='RSI')
        assert signal['signal'] in ['BUY', 'SELL', 'HOLD']
        assert 0 <= signal['confidence'] <= 1
        
        # 3. Validate risk
        if signal['signal'] == 'BUY':
            approved = risk.validate_trade(
                'BTCUSDT', 'BUY', 0.1, data['close']
            )
            assert approved['approved'] == True
            
            # 4. Execute trade
            order = execution.place_order(
                'BTCUSDT', 'BUY', 'LIMIT', 0.1, data['close']
            )
            assert 'order_id' in order
            
            # 5. Record in portfolio
            portfolio.record_trade({
                'symbol': 'BTCUSDT',
                'side': 'BUY',
                'quantity': 0.1,
                'price': data['close'],
                'fee': 5.00
            })
            
            # 6. Verify portfolio
            positions = portfolio.get_all_positions()
            assert len(positions) == 1
            assert positions[0]['symbol'] == 'BTCUSDT'
            assert positions[0]['quantity'] == 0.1
```

### Test Database Pattern

**Using In-Memory SQLite for Fast Tests:**
```python
@pytest.fixture
def portfolio_db():
    """Create in-memory SQLite database for testing"""
    pm = PortfolioManager(':memory:')  # Use :memory: instead of file
    yield pm
    # Cleanup automatic - no file to delete

def test_portfolio_operations(portfolio_db):
    # Add trades
    portfolio_db.record_trade({
        'symbol': 'BTCUSDT', 'side': 'BUY',
        'quantity': 0.1, 'price': 43000, 'fee': 5
    })
    
    # Verify
    positions = portfolio_db.get_all_positions()
    assert len(positions) == 1
```

### Testing Async Code

**Async Test Pattern:**
```python
import pytest
import asyncio

@pytest.mark.asyncio
async def test_fetch_prices_batch():
    """Test concurrent price fetching"""
    async with AsyncMarketDataAgent() as agent:
        symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
        prices = await agent.fetch_prices_batch(symbols)
        
        assert len(prices) == 3
        assert all('price' in p for p in prices)
```

### Mocking Binance API

**Mock for Testnet Operations:**
```python
@pytest.fixture
def mock_binance_client():
    """Mock Binance API responses"""
    with patch('binance_trade_agent.binance_client.Client') as mock:
        mock.get_account.return_value = {
            'balances': [
                {'asset': 'USDT', 'free': '10000.00'},
                {'asset': 'BTC', 'free': '0.1'}
            ]
        }
        mock.create_order.return_value = {
            'orderId': 123456,
            'status': 'NEW'
        }
        yield mock
```

---

## Performance & Optimization

### Connection Pooling

**Async Client with Connection Pooling:**
```python
class AsyncBinanceClient:
    def __init__(self, pool_size=10):
        self.connector = TCPConnector(
            limit=pool_size,
            limit_per_host=5,
            ttl_dns_cache=300
        )
        self.session = None
    
    async def __aenter__(self):
        self.session = ClientSession(connector=self.connector)
        return self
    
    async def __aexit__(self, *args):
        await self.session.close()
    
    async def get_price(self, symbol):
        # Reuses connection from pool
        async with self.session.get(f'/price?symbol={symbol}') as resp:
            return await resp.json()

# Usage
async with AsyncBinanceClient(pool_size=20) as client:
    # All requests reuse pool connections
    prices = await asyncio.gather(*[
        client.get_price(symbol) for symbol in symbols
    ])
```

### Concurrent Operations

**Batch Processing:**
```python
async def fetch_all_prices(symbols):
    """Fetch 100+ symbols concurrently"""
    async with AsyncBinanceClient() as client:
        # Create tasks for all symbols
        tasks = [client.get_price(s) for s in symbols]
        
        # Execute concurrently with limit
        semaphore = asyncio.Semaphore(20)  # Max 20 concurrent
        
        async def bounded_fetch(symbol):
            async with semaphore:
                return await client.get_price(symbol)
        
        return await asyncio.gather(*[
            bounded_fetch(s) for s in symbols
        ])

# 100 symbols in ~5 seconds instead of ~100 seconds
```

### Database Query Optimization

**Indexing:**
```python
# Create indexes for frequently queried columns
from sqlalchemy import Index

class TradeORM(Base):
    __tablename__ = 'trades'
    trade_id = Column(String, primary_key=True)
    symbol = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False)
    
    __table_args__ = (
        Index('idx_symbol_created', 'symbol', 'created_at'),
        Index('idx_symbol', 'symbol'),
    )
```

**Query Optimization:**
```python
# ❌ SLOW - N+1 query problem
for position in positions:
    trade = session.query(Trade).filter_by(id=position.trade_id).first()

# ✅ FAST - Single query with join
positions = session.query(Position).join(Trade).all()
```

### Caching Strategy

**Function Result Caching:**
```python
import functools
from datetime import datetime, timedelta

class CachedAgent:
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 60  # 60 seconds
    
    def cached_fetch(self, symbol):
        """Cache price for 60 seconds"""
        cache_key = f"price_{symbol}"
        now = datetime.now()
        
        if cache_key in self.cache:
            cached_value, timestamp = self.cache[cache_key]
            if (now - timestamp).total_seconds() < self.cache_ttl:
                return cached_value
        
        # Fetch fresh data
        value = self._fetch_from_api(symbol)
        self.cache[cache_key] = (value, now)
        return value
    
    def _fetch_from_api(self, symbol):
        # Actual API call
        pass
```

### Memory Management

**Generator for Large Datasets:**
```python
# ❌ BAD - Loads all trades into memory
def get_all_trades():
    trades = []
    for row in session.query(Trade).all():
        trades.append(format_trade(row))
    return trades

# ✅ GOOD - Streams trades one at a time
def get_all_trades():
    for row in session.query(Trade).yield_per(100):
        yield format_trade(row)

# Usage
for trade in get_all_trades():
    process(trade)  # Never loads more than 100 in memory
```

---

## Extending the System

### Adding a New Strategy

**1. Create Strategy Module** (`strategies/new_strategy.py`):
```python
from binance_trade_agent.strategies import SignalType

def analyze_new_strategy(prices, period=14):
    """Analyze using custom strategy"""
    
    # Calculate custom indicator
    indicator = calculate_custom_indicator(prices, period)
    
    # Generate signal
    if indicator > threshold_high:
        signal = SignalType.BUY
        confidence = min(1.0, (indicator - threshold_high) / 100)
    elif indicator < threshold_low:
        signal = SignalType.SELL
        confidence = min(1.0, (threshold_low - indicator) / 100)
    else:
        signal = SignalType.HOLD
        confidence = 0.5
    
    return {
        'signal': signal,
        'confidence': confidence,
        'indicator_value': indicator,
        'thresholds': {'high': threshold_high, 'low': threshold_low}
    }
```

**2. Register in SignalAgent:**
```python
# In signal_agent.py
class SignalAgent:
    STRATEGIES = {
        'RSI': self._analyze_rsi,
        'MACD': self._analyze_macd,
        'NEW_STRATEGY': analyze_new_strategy  # Add your strategy
    }
```

**3. Test the Strategy:**
```python
def test_new_strategy():
    prices = [100 + i for i in range(20)]
    result = analyze_new_strategy(prices)
    
    assert result['signal'] in [SignalType.BUY, SignalType.SELL, SignalType.HOLD]
    assert 0 <= result['confidence'] <= 1
```

### Adding a New Risk Control

**1. Extend RiskManagementAgent:**
```python
class RiskManagementAgent:
    def __init__(self):
        self.config = {...}
        self.controls = [
            self._check_position_size,
            self._check_stop_loss,
            self._check_portfolio_heat,
            self._check_new_control,  # Add new control
        ]
    
    def _check_new_control(self, trade_params):
        """New risk control logic"""
        symbol = trade_params['symbol']
        quantity = trade_params['quantity']
        
        # Custom validation
        if violates_custom_rule(symbol, quantity):
            return {
                'approved': False,
                'reason': 'Violates custom rule'
            }
        
        return {'approved': True}
```

### Adding an MCP Tool

**1. Create Tool Function:**
```python
async def my_custom_tool(param1, param2):
    """Do something useful"""
    result = await process(param1, param2)
    return {
        'status': 'success',
        'data': result
    }
```

**2. Register in MCP Server:**
```python
# In mcp_server.py
TOOLS = {
    'my_custom_tool': {
        'description': 'Tool description',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'param1': {'type': 'string'},
                'param2': {'type': 'number'}
            },
            'required': ['param1', 'param2']
        }
    }
}

async def handle_tool_call(tool_name, arguments):
    if tool_name == 'my_custom_tool':
        return await my_custom_tool(**arguments)
```

---

## Common Gotchas

### Import Errors

**Problem:** `ModuleNotFoundError: No module named 'binance_trade_agent'`

**Cause:** Package not installed in editable mode after code changes in Docker

**Solution:**
```bash
# Rebuild container (triggers pip install -e .)
docker-compose build --no-cache

# Or locally
pip install -e .
```

**Always Use Absolute Imports:**
```python
# ✅ CORRECT
from binance_trade_agent.portfolio_manager import PortfolioManager
from binance_trade_agent.strategies import SignalType

# ❌ WRONG (relative imports fail in Docker)
from ..portfolio_manager import PortfolioManager
from .strategies import SignalType
```

### Database Locking

**Problem:** "database is locked" when running tests

**Cause:** Multiple processes accessing same SQLite file

**Solution:**
```python
# Use :memory: for tests instead of file
pm_test = PortfolioManager(':memory:')  # Each test gets isolated DB

# Or use different database per test
@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test.db"
    return PortfolioManager(str(db_file))
```

### Async Event Loop Issues

**Problem:** "RuntimeError: Event loop is closed" or "asyncio.run() cannot be called from running event loop"

**Cause:** Mixing async/sync code or not properly closing loop

**Solution:**
```python
# ✅ CORRECT - Use context manager
async with AsyncBinanceClient() as client:
    price = await client.get_price('BTCUSDT')

# ❌ WRONG - Forgetting to close
client = AsyncBinanceClient()
price = await client.get_price('BTCUSDT')
# Session never closed - resource leak

# ✅ CORRECT - Use pytest.mark.asyncio
@pytest.mark.asyncio
async def test_async():
    async with AsyncClient() as client:
        await client.do_something()
```

### ORM Object Attributes

**Problem:** `AttributeError: 'TradeORM' object has no attribute 'symbol'`

**Cause:** Accessing unmapped column or lazy-loaded relationship not initialized

**Solution:**
```python
# Define all columns in ORM class
class TradeORM(Base):
    __tablename__ = 'trades'
    trade_id = Column(String, primary_key=True)
    symbol = Column(String, nullable=False)  # Define column
    side = Column(String, nullable=False)
    # ... etc

# For relationships, use relationship() properly
class Position(Base):
    trades = relationship('TradeORM', lazy='joined')  # Eager load
```

### Cache Staleness

**Problem:** Web UI shows outdated portfolio data after trades

**Cause:** Streamlit caching not invalidated after portfolio updates

**Solution:**
```python
# Use cache_control in Streamlit
import streamlit as st

@st.cache_data(ttl=5)  # Re-cache every 5 seconds
def get_portfolio():
    return PortfolioManager().get_portfolio_stats()

# Or disable cache for critical operations
st.cache_data.clear()  # Clear all cache
```

### Correlation ID Missing

**Problem:** Cannot trace operations through logs

**Cause:** Forgetting to pass correlation_id to logger

**Solution:**
```python
# Always include correlation_id
extra = {'correlation_id': correlation_id}
self.logger.info("Operation started", extra=extra)

# Use middleware to auto-add correlation ID
class CorrelationIdMiddleware:
    def __call__(self, environ, start_response):
        correlation_id = str(uuid4())
        environ['correlation_id'] = correlation_id
        return self.app(environ, start_response)
```

---

## Debugging & Logging

### Debug Logging Setup

```python
import logging
import sys

def setup_debug_logging():
    # Root logger
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    
    # Console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    
    # Format with correlation ID
    formatter = logging.Formatter(
        '[%(asctime)s] [%(name)s] [%(levelname)s] '
        '[%(correlation_id)s] %(message)s',
        defaults={'correlation_id': 'N/A'}
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)

setup_debug_logging()
```

### Viewing Docker Logs

```bash
# Live logs with timestamps
docker-compose logs -f --timestamps trading-agent

# Last 100 lines
docker-compose logs --tail=100 trading-agent

# Logs since 5 minutes ago
docker-compose logs --since 5m trading-agent

# Filter by keyword
docker-compose logs trading-agent | grep "ERROR"
```

### Database Debugging

```bash
# Access SQLite database directly
docker-compose exec trading-agent sqlite3 /app/data/web_portfolio.db

# Query trades
sqlite> SELECT * FROM trades LIMIT 5;

# Query positions
sqlite> SELECT * FROM positions;

# Check database schema
sqlite> .schema

# Export data as CSV
sqlite> .mode csv
sqlite> .output trades.csv
sqlite> SELECT * FROM trades;
```

### Performance Profiling

```python
import cProfile
import pstats

def profile_operation():
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Run operation to profile
    market_data_agent.fetch_data('BTCUSDT')
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)  # Print top 10 slowest functions
```

---

**For Architecture Questions:** See COMPREHENSIVE_GUIDE.md  
**For AI Integration:** See .github/copilot-instructions.md  
**For Deployment:** See COMPREHENSIVE_GUIDE.md Deployment section

**Last Updated:** November 9, 2025  
**Status:** Complete  
**Python:** 3.10+
