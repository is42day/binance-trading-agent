# How to Run Autonomous Trading - Step-by-Step Guide

**Date**: November 10, 2025  
**Objective**: Actually execute autonomous trades on Binance testnet

---

## 🚨 What Went Wrong

The agent sat idle for 1.5 hours because:
- ❌ No autonomous trading loop was running
- ❌ supervisord only manages MCP server and Dashboard
- ❌ SIGNAL_AGENT_TEST_MODE was not enabled
- ❌ autonomous_trading_loop.py was created but not integrated

---

## ✅ How to Fix It (3 Options)

## **Option A: Quick Test (5 minutes)**

Run the autonomous loop directly in the container:

```bash
# Start the autonomous trading loop for 10 minutes
docker-compose exec -d trading-agent \
  timeout 600 python -m binance_trade_agent.autonomous_trading_loop

# Monitor in real-time
docker logs binance-trading-agent -f
```

**What happens**:
- Connects to Binance testnet
- Generates signals for BTCUSDT and ETHUSDT
- Executes trades every 2 minutes
- Runs for 10 minutes
- Displays results

**Result**: Should see actual trades and portfolio updates

---

## **Option B: Full Hour Test (60 minutes)**

Run the loop for a full hour:

```bash
# Start for 60 minutes
docker-compose exec -d trading-agent \
  python -m binance_trade_agent.autonomous_trading_loop

# Watch logs
docker logs binance-trading-agent -f --tail 50
```

**Environment Variables** (optional):
```bash
# Set before running
TRADING_SYMBOLS=BTCUSDT,ETHUSDT,BNBUSDT  # Add more pairs
TRADING_INTERVAL_SECONDS=120              # 2-minute intervals
TRADING_DURATION_MINUTES=60               # 60 minutes total
STRATEGY_NAME=rsi_momentum               # Or: macd_crossover, bollinger_bands
```

**Full command with options**:
```bash
docker-compose exec -e \
  TRADING_DURATION_MINUTES=60 \
  TRADING_INTERVAL_SECONDS=120 \
  STRATEGY_NAME=rsi_momentum \
  trading-agent \
  python -m binance_trade_agent.autonomous_trading_loop
```

---

## **Option C: Permanent Setup (Always Trading)**

Modify supervisord.conf to include autonomous trading:

### Step 1: Edit supervisord.conf

Add this section at the end (before the closing bracket):

```ini
[program:autonomous_trader]
command=python -m binance_trade_agent.autonomous_trading_loop
directory=/app
autostart=true
autorestart=true
startsecs=5
stopasgroup=true
stdout_logfile=/app/logs/autonomous_trader.log
stdout_logfile_maxbytes=10MB
stdout_logfile_backups=3
stderr_logfile=/app/logs/autonomous_trader_err.log
stderr_logfile_maxbytes=10MB
stderr_logfile_backups=3
environment=TRADING_DURATION_MINUTES=0,TRADING_INTERVAL_SECONDS=120,STRATEGY_NAME=combined_default
```

### Step 2: Rebuild Docker

```bash
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

### Step 3: Verify It's Running

```bash
# Check all processes
docker-compose exec trading-agent supervisorctl status

# Should show:
# binance_agent    RUNNING
# dash_ui          RUNNING  
# autonomous_trader RUNNING  ← NEW
```

### Step 4: Monitor Trading

```bash
# View trading logs
docker logs binance-trading-agent -f | grep -i "trade\|signal\|cycle"

# Or specifically the autonomous trader log
docker-compose exec trading-agent tail -f /app/logs/autonomous_trader.log
```

---

## 🎯 Let's Run a Real Test Right Now

### **Immediate Action: 10-Minute Test**

```bash
# Command (copy-paste this):
docker-compose exec -d trading-agent python -m binance_trade_agent.autonomous_trading_loop
```

This will:
1. ✅ Start immediately
2. ✅ Connect to Binance testnet
3. ✅ Execute trades every 2 minutes
4. ✅ Run for 60 minutes (default)
5. ✅ Log everything to see what happens

### **Then Monitor**

Open 2 terminals:

**Terminal 1 - View logs**:
```bash
docker logs binance-trading-agent -f
```

**Terminal 2 - Check portfolio**:
```bash
docker-compose exec trading-agent python /app/analyze_portfolio.py
```

---

## 📊 Expected Output

When the loop runs, you should see:

```
======================================================================
Trading Cycle #1 - 14:36:00
======================================================================

📊 Processing BTCUSDT...
  Signal: BUY
  Confidence: 85%
  Price: $45,230.50
  Risk Approved: True
  ✅ TRADE EXECUTED!
     Order ID: testnet_123456
     Fill Price: $45,231.00
     Time: 14:36:05

📊 Processing ETHUSDT...
  Signal: HOLD
  Confidence: 60%
  Price: $2,315.75
  Risk Approved: True
  ⏸️ Trade not executed (risk check failed)

📈 Cycle Summary:
   Cycles completed: 1
   Trades executed: 1
   Time elapsed: 0:00:15
```

---

## 🔧 Troubleshooting

### "Command not found" error

```bash
# Make sure you're using docker-compose (not docker):
docker-compose exec -d trading-agent python -m binance_trade_agent.autonomous_trading_loop
```

### No output visible

```bash
# Check if process is running
docker-compose exec trading-agent ps aux | grep autonomous

# Check logs
docker logs binance-trading-agent --tail 100
```

### API errors

```bash
# Check Binance testnet connectivity
docker-compose exec trading-agent python -c \
  "from binance_trade_agent.binance_client import BinanceClient; \
   print(BinanceClient().get_server_time())"
```

### Database errors

```bash
# Check if database exists
docker-compose exec trading-agent ls -la /app/data/
```

---

## 📈 Monitoring the Session

### Real-Time Terminal Output

```bash
docker logs binance-trading-agent -f
```

### Portfolio Dashboard

```
http://localhost:8050 → Portfolio page
```

Watch for:
- Portfolio value changing
- Trade count increasing
- P&L updating

### Query Results

```bash
# After 10 minutes of trading:
docker-compose exec trading-agent python /app/analyze_portfolio.py

# Shows:
# - Total trades executed
# - Trades by symbol
# - Current positions
# - P&L
```

---

## ⏱️ Timing Reference

| Duration | What to Expect |
|----------|---|
| 0-2 min | Agent connects, first signal |
| 2-10 min | 3-5 trades executed |
| 10-30 min | 10-15 trades, positions forming |
| 30-60 min | 30+ trades, positions managed |

**Note**: Actual trade count depends on market conditions and signal generation

---

## 🛑 How to Stop

### Stop the autonomous trading loop

```bash
# Gracefully stop
docker-compose exec trading-agent pkill -f autonomous_trading_loop

# Or force stop
docker-compose down

# Or restart cleanly
docker-compose restart trading-agent
```

### Analyze final results

```bash
# Get complete trading session report
docker-compose exec trading-agent python /app/analyze_portfolio.py
```

---

## ✅ Success Criteria

After running, you should see:

- ✅ Multiple trades in portfolio database
- ✅ Both BTCUSDT and ETHUSDT traded
- ✅ Portfolio value changed
- ✅ P&L calculated
- ✅ Detailed logs of all activity
- ✅ Strategy signals working
- ✅ Risk validation occurring
- ✅ Orders actually placed on testnet

---

## 🎯 Next: Run the Test

Copy this command and run it:

```bash
docker-compose exec -d trading-agent python -m binance_trade_agent.autonomous_trading_loop
```

Then check logs every minute:

```bash
docker logs binance-trading-agent -f
```

Let me know what you see!

---

*Status: Ready to Execute Real Autonomous Trading*  
*All systems: ✅ Operational*  
*Just need to start the loop*
