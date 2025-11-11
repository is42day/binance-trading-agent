# Quick Start Guide - Autonomous Trading Agent

**Date**: November 10, 2025  
**Status**: ✅ READY TO TRADE

---

## 🚀 Start Trading in 5 Minutes

### Step 1: Choose Your Mode

```bash
# Option A: TEST MODE (Fastest - Recommended First)
SIGNAL_AGENT_TEST_MODE=true docker-compose up -d

# Option B: DEMO MODE (No API keys needed)
DEMO_MODE=true python -m binance_trade_agent.main

# Option C: TESTNET MODE (Real data, zero risk)
BINANCE_TESTNET=true \
BINANCE_API_KEY=<your_testnet_key> \
BINANCE_API_SECRET=<your_testnet_secret> \
docker-compose up -d
```

---

### Step 2: Verify It's Running

```bash
# Check services
docker-compose ps

# Should show:
# ✅ binance-trading-agent (RUNNING)
# ✅ redis (RUNNING)
```

---

### Step 3: Monitor Trading Activity

**Option A: View Logs**
```bash
docker logs binance-trading-agent -f
```

**Option B: Open Dashboard**
```
http://localhost:8050
```

**Option C: Use CLI**
```bash
docker-compose exec trading-agent python -m binance_trade_agent.cli
```

---

## 📊 What Happens Automatically

When you start the agent, it:

```
1. ✅ Connects to Binance (testnet by default)
2. ✅ Fetches market data
3. ✅ Generates trading signals
4. ✅ Validates risk limits
5. ✅ Places orders automatically
6. ✅ Tracks portfolio P&L
7. ✅ Repeats continuously
```

**No manual intervention needed!**

---

## 🎯 Try Different Strategies

### Switch Strategy (Runtime)

Via **Dashboard**: Advanced Controls → Trading Strategy → Select

Via **CLI**:
```bash
docker-compose exec trading-agent python -m binance_trade_agent.cli

# Then:
(trading) strategy set rsi_momentum
(trading) signal generate BTCUSDT
```

Via **Environment**:
```bash
STRATEGY_NAME=macd_crossover docker-compose up -d
```

---

## 📈 Available Strategies

| Strategy | Trigger | Best For |
|----------|---------|----------|
| **RSI Momentum** | RSI > 70 (sell), < 30 (buy) | Trending markets |
| **MACD Crossover** | MACD line crosses signal | Momentum trades |
| **Bollinger Bands** | Price beyond bands | Mean reversion |
| **Combined** (Default) | Consensus of multiple | Balanced approach |

---

## ⚙️ Adjust Risk Settings

### Current Defaults
```
Max Position: 5% of portfolio
Stop Loss: 2%
Take Profit: 6%
Max Daily Loss: 5%
```

### Customize (Via Environment)
```bash
RISK_MAX_POSITION_PER_SYMBOL=0.08 \
RISK_DEFAULT_STOP_LOSS_PCT=0.03 \
RISK_MAX_DAILY_DRAWDOWN=0.10 \
docker-compose up -d
```

### Via Dashboard
Advanced Controls → Risk Management → Adjust → Save

---

## 🛑 Stop Trading

```bash
# Graceful shutdown
docker-compose down

# Emergency stop (via dashboard)
Navigate to Advanced → Press "Emergency Stop"

# Emergency stop (via CLI)
(trading) emergency
```

---

## 📋 Monitoring Checklist

**During Autonomous Trading**:

- [ ] Dashboard showing live data
- [ ] Orders appearing in logs
- [ ] Portfolio updating
- [ ] No error spikes
- [ ] System healthy

**Check every 30 minutes initially**

---

## 🔧 Troubleshooting

### Agent not trading?
```bash
# Check logs
docker logs binance-trading-agent -f | grep -i "signal\|order\|trade"

# Verify it's running
docker-compose ps

# Check configuration
docker-compose exec trading-agent env | grep -i signal
```

### Port already in use?
```bash
# Find process on port 8050
lsof -i :8050

# Or use different port
DASHBOARD_PORT=8051 docker-compose up -d
```

### Connection errors?
```bash
# Test API connectivity
docker-compose exec trading-agent python -c \
  "from binance_trade_agent.binance_client import BinanceClient; \
   client = BinanceClient(); \
   print(client.get_server_time())"
```

---

## 📚 Advanced Options

### Run Multiple Strategies Concurrently

```bash
# Terminal 1: RSI strategy
STRATEGY_NAME=rsi_momentum docker-compose up -d

# Terminal 2: MACD strategy (different container)
PORT_OFFSET=1 STRATEGY_NAME=macd_crossover docker-compose up -d

# Compare results
# Dashboard shows both strategies trading same symbols
```

### Custom Strategy Parameters

```bash
# Launch with custom RSI levels
STRATEGY_NAME=custom_rsi \
SIGNAL_RSI_OVERBOUGHT=75 \
SIGNAL_RSI_OVERSOLD=25 \
python -m binance_trade_agent.main
```

### Enable All Logging

```bash
LOG_LEVEL=DEBUG \
ENABLE_CORRELATION_IDS=true \
docker-compose up -d

# Detailed logs:
docker logs binance-trading-agent -f | grep "correlation_id"
```

---

## 💰 Trading Amounts

### Adjust Trade Size

```bash
# BTC default: 0.001 (about $45)
TRADING_DEFAULT_QUANTITY_BTC=0.002 \

# ETH default: 0.01 (about $25)
TRADING_DEFAULT_QUANTITY_ETH=0.02 \

# Start smaller for testing:
TRADING_DEFAULT_QUANTITY_BTC=0.0001
```

---

## 🔐 Production Readiness Checklist

Before switching to live trading:

- [ ] Tested on testnet for 24+ hours
- [ ] Profitable or breakeven strategy confirmed
- [ ] Risk limits set aggressively (2% max drawdown)
- [ ] Position sizes small (0.001 BTC or less)
- [ ] 24/7 monitoring capability available
- [ ] Emergency stop tested
- [ ] Backup API keys available
- [ ] Network connection stable

---

## 📞 Getting Help

### View Dashboard Logs
```
http://localhost:8050/logs
```

### Check Agent Logs
```bash
docker logs binance-trading-agent --tail 100
```

### Run Diagnostics
```bash
docker-compose exec trading-agent python -m binance_trade_agent.cli
> status
> metrics
> config
```

### Restart Fresh
```bash
docker-compose down -v
docker-compose up -d
```

---

## ✅ You're All Set!

Your trading agent is:
- ✅ Fully configured
- ✅ Running successfully
- ✅ Ready to trade autonomously
- ✅ Monitoring portfolio in real-time
- ✅ Adapting strategies automatically

**Start trading now** with one of the commands above.

---

*Status: Production Ready | Last Updated: 2025-11-10*
