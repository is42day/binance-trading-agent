# Binance Trading Agent - Documentation

This directory contains comprehensive documentation for the Binance Trading Agent system.

## Quick Navigation

### 🚀 Getting Started
- **[../../README.md](../README.md)** - Main project README with overview and setup
- **[AUTONOMOUS_TRADING_CAPABILITY.md](AUTONOMOUS_TRADING_CAPABILITY.md)** - Complete guide to autonomous trading features
- **[QUICK_START_AUTONOMOUS_TRADING.md](QUICK_START_AUTONOMOUS_TRADING.md)** - 5-minute quick start guide
- **[RUN_AUTONOMOUS_TRADING_NOW.md](RUN_AUTONOMOUS_TRADING_NOW.md)** - Step-by-step execution guide

### 📚 Reference Guides
- **[COMPREHENSIVE_GUIDE.md](COMPREHENSIVE_GUIDE.md)** - Full system documentation
- **[DEVELOPMENT_REFERENCE.md](DEVELOPMENT_REFERENCE.md)** - Developer reference
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Quick lookup reference
- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - Testing procedures

### 🎨 Design & UI
- **[DESIGN_SYSTEM_IMPLEMENTATION.md](DESIGN_SYSTEM_IMPLEMENTATION.md)** - Design system details
- **[DESIGN_SYSTEM_QUICK_REFERENCE.md](DESIGN_SYSTEM_QUICK_REFERENCE.md)** - Design system quick ref
- **[DESIGN_SYSTEM_STATUS.md](DESIGN_SYSTEM_STATUS.md)** - Design system status
- **[CSS_VARIABLES_REFERENCE.md](CSS_VARIABLES_REFERENCE.md)** - CSS variables documentation
- **[CSS_DEBUG_REPORT.md](CSS_DEBUG_REPORT.md)** - CSS debugging guide
- **[DASHBOARD_TEST_RESULTS.md](DASHBOARD_TEST_RESULTS.md)** - Dashboard test results
- **[DASH_MIGRATION_PLAN.md](DASH_MIGRATION_PLAN.md)** - Streamlit to Dash migration details
- **[UI_UNIFICATION_PROGRESS.md](UI_UNIFICATION_PROGRESS.md)** - UI unification progress

### 🏥 System Health & Monitoring
- **[SYSTEM_HEALTH_UI_SUMMARY.md](SYSTEM_HEALTH_UI_SUMMARY.md)** - System health overview
- **[SYSTEM_HEALTH_UI_DESIGN_PLAN.md](SYSTEM_HEALTH_UI_DESIGN_PLAN.md)** - Health UI design plan
- **[SYSTEM_HEALTH_UI_DESIGN_DETAILS.md](SYSTEM_HEALTH_UI_DESIGN_DETAILS.md)** - Health UI details
- **[SYSTEM_HEALTH_UI_APPROVAL_REQUEST.md](SYSTEM_HEALTH_UI_APPROVAL_REQUEST.md)** - Health UI approval
- **[LIVE_TRADING_SESSION_MONITOR.md](LIVE_TRADING_SESSION_MONITOR.md)** - Live trading monitoring

### 📊 Session Reports

#### Trading Session Logs
Reports and analysis from recent trading sessions:
- **[session-logs/EXECUTIVE_SUMMARY_TRADING_SESSION.md](session-logs/EXECUTIVE_SUMMARY_TRADING_SESSION.md)** - Executive summary of trading findings
- **[session-logs/TRADING_SESSION_ANALYSIS.md](session-logs/TRADING_SESSION_ANALYSIS.md)** - Detailed trading session analysis
- **[session-logs/SESSION_SUMMARY_TRADING_ANALYSIS.md](session-logs/SESSION_SUMMARY_TRADING_ANALYSIS.md)** - Trading session recap
- **[session-logs/SESSION_SUMMARY_AUTONOMOUS_ANALYSIS.md](session-logs/SESSION_SUMMARY_AUTONOMOUS_ANALYSIS.md)** - Autonomous analysis summary
- **[session-logs/COMPLETE_SESSION_DELIVERABLES.md](session-logs/COMPLETE_SESSION_DELIVERABLES.md)** - All deliverables from session

#### Phase Reports
Development phase reports and milestones:
- **[phase-reports/](phase-reports/)** - All phase completion reports (PHASE_2-9)

### 🔧 Implementation Guides
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - Implementation summary
- **[DOCUMENTATION_CONSOLIDATION_COMPLETE.md](DOCUMENTATION_CONSOLIDATION_COMPLETE.md)** - Documentation consolidation

### 📈 Status & Progress
- **[PROGRESS.md](PROGRESS.md)** - Overall project progress
- **[COMPLETE_AUTONOMOUS_TRADING_STATUS.md](COMPLETE_AUTONOMOUS_TRADING_STATUS.md)** - Autonomous trading status

## Key Features

### Trading System
- ✅ Autonomous trading agent with multiple strategies (RSI, MACD, Bollinger Bands)
- ✅ Real-time market data integration with Binance testnet
- ✅ Multi-symbol trading support
- ✅ Advanced risk management with position limits
- ✅ Portfolio tracking and P&L calculations
- ✅ Correlation ID tracking for all operations

### Dashboard
- ✅ 7-page Plotly Dash interface
- ✅ Real-time market data visualization
- ✅ Trading signal generation display
- ✅ Portfolio and position tracking
- ✅ Trade history and logs
- ✅ Comprehensive design system

### Architecture
- ✅ Agent-based orchestration (MarketData → Signal → Risk → Execution)
- ✅ Model Context Protocol (MCP) integration
- ✅ Docker containerization with supervisord
- ✅ Async/await optimization for performance
- ✅ SQLite database for persistence
- ✅ Redis caching layer

## For Different Roles

### 🚀 If you want to RUN autonomous trading:
1. Start with: **[QUICK_START_AUTONOMOUS_TRADING.md](QUICK_START_AUTONOMOUS_TRADING.md)**
2. Then follow: **[RUN_AUTONOMOUS_TRADING_NOW.md](RUN_AUTONOMOUS_TRADING_NOW.md)**

### 👨‍💻 If you want to DEVELOP features:
1. Read: **[DEVELOPMENT_REFERENCE.md](DEVELOPMENT_REFERENCE.md)**
2. Reference: **[COMPREHENSIVE_GUIDE.md](COMPREHENSIVE_GUIDE.md)**
3. Test with: **[TESTING_GUIDE.md](TESTING_GUIDE.md)**

### 🎨 If you want to MODIFY the UI:
1. Study: **[DESIGN_SYSTEM_IMPLEMENTATION.md](DESIGN_SYSTEM_IMPLEMENTATION.md)**
2. Reference: **[DESIGN_SYSTEM_QUICK_REFERENCE.md](DESIGN_SYSTEM_QUICK_REFERENCE.md)**
3. Debug with: **[CSS_DEBUG_REPORT.md](CSS_DEBUG_REPORT.md)**

### 📊 If you want to UNDERSTAND recent changes:
1. Read: **[session-logs/EXECUTIVE_SUMMARY_TRADING_SESSION.md](session-logs/EXECUTIVE_SUMMARY_TRADING_SESSION.md)**
2. Review: **[phase-reports/](phase-reports/)**
3. Deep dive: **[session-logs/](session-logs/)**

## Directory Structure

```
docs/
├── README.md (this file)
├── AUTONOMOUS_TRADING_CAPABILITY.md
├── QUICK_START_AUTONOMOUS_TRADING.md
├── RUN_AUTONOMOUS_TRADING_NOW.md
├── COMPREHENSIVE_GUIDE.md
├── DEVELOPMENT_REFERENCE.md
├── TESTING_GUIDE.md
├── DESIGN_SYSTEM_*.md
├── DASHBOARD_TEST_RESULTS.md
├── CSS_*.md
├── UI_UNIFICATION_PROGRESS.md
├── SYSTEM_HEALTH_*.md
├── LIVE_TRADING_SESSION_MONITOR.md
├── PROGRESS.md
├── COMPLETE_AUTONOMOUS_TRADING_STATUS.md
├── session-logs/
│   ├── EXECUTIVE_SUMMARY_TRADING_SESSION.md
│   ├── TRADING_SESSION_ANALYSIS.md
│   ├── SESSION_SUMMARY_TRADING_ANALYSIS.md
│   ├── SESSION_SUMMARY_AUTONOMOUS_ANALYSIS.md
│   └── COMPLETE_SESSION_DELIVERABLES.md
└── phase-reports/
    ├── PHASE_2_COMPLETE.md
    ├── PHASE_3_COMPLETE.md
    ├── PHASE_3_SUMMARY.md
    ├── PHASE_7_8_FUNCTIONALITY_COMPLETE.md
    ├── PHASE_8_UI_UX_STATUS.md
    ├── PHASE_9_TESTING_REPORT.md
    └── ...
```

## Quick Commands

```bash
# Run autonomous trading for 60 minutes
docker-compose exec -d trading-agent python -m binance_trade_agent.autonomous_trading_loop

# Monitor logs
docker logs binance-trading-agent -f

# Analyze trading results
docker-compose exec trading-agent python /app/analyze_portfolio.py

# Start the dashboard
docker-compose up -d
```

## Key Documentation Highlights

### Most Important Files
1. **[../README.md](../README.md)** - Start here!
2. **[QUICK_START_AUTONOMOUS_TRADING.md](QUICK_START_AUTONOMOUS_TRADING.md)** - 5-min setup
3. **[RUN_AUTONOMOUS_TRADING_NOW.md](RUN_AUTONOMOUS_TRADING_NOW.md)** - Execution guide
4. **[COMPREHENSIVE_GUIDE.md](COMPREHENSIVE_GUIDE.md)** - Full reference

### Most Recent Changes
- **[session-logs/EXECUTIVE_SUMMARY_TRADING_SESSION.md](session-logs/EXECUTIVE_SUMMARY_TRADING_SESSION.md)** - Latest trading session summary
- **[phase-reports/](phase-reports/)** - Recent phase completions

## Support

### Common Questions
See **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** for answers to common questions.

### Troubleshooting
See **[RUN_AUTONOMOUS_TRADING_NOW.md](RUN_AUTONOMOUS_TRADING_NOW.md)** troubleshooting section.

### More Information
See **[DEVELOPMENT_REFERENCE.md](DEVELOPMENT_REFERENCE.md)** for technical details.

## Last Updated
- Structure reorganized: November 11, 2025
- Latest trading session: November 10, 2025
- Latest phase completion: Phase 9 (Docker & Testing)

---

**Note:** This documentation directory is continuously updated as new features and improvements are made. Check the README at the root of the project for the latest updates.
