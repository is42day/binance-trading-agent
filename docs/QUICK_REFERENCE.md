# 📚 Documentation Quick Reference Card

Print this or bookmark - tells you exactly which doc to read for what you need.

---

## 🎯 Choose Your Path

### 🚀 **I want to get started in 5 minutes**
→ **README.md** (3KB, ~80 lines)
- Testnet setup
- Quick start steps
- Key features
- Links to full docs

### 📖 **I need complete documentation (comprehensive)**
→ **COMPREHENSIVE_GUIDE.md** (28KB, ~1,200 lines)
- Architecture overview
- Installation options
- Complete usage guides (CLI, Web UI, API)
- Testing guide
- Deployment (Docker)
- Risk management
- Troubleshooting & recovery steps

### 👨‍💻 **I'm developing / writing code**
→ **DEVELOPMENT_REFERENCE.md** (30KB, ~900 lines)
- Development environment setup
- Architecture patterns (agent, error handling, async)
- Complete API reference
- Testing strategies & patterns
- Performance optimization
- How to extend the system
- Common gotchas & debugging

### 🤖 **I'm integrating with AI / Claude**
→ **.github/copilot-instructions.md**
- AI assistant patterns
- Architecture guidance
- Deployment requirements
- Best practices

### 📦 **I need package-level docs**
→ **binance_trade_agent/README.md**
- Module organization
- Component documentation
- Package setup details

---

## 🔍 Quick Lookup by Topic

| Topic | Where to Find | File & Section |
|-------|---------------|---|
| Get Started | First 5 min | README.md |
| Architecture | Overview | COMPREHENSIVE_GUIDE.md → Architecture Overview |
| Installation | Docker/Local setup | COMPREHENSIVE_GUIDE.md → Installation & Setup |
| Web UI Usage | Using dashboard | COMPREHENSIVE_GUIDE.md → Web UI Features |
| Trading Signals | Signal generation | COMPREHENSIVE_GUIDE.md → Usage Guides |
| Risk Management | Risk controls | COMPREHENSIVE_GUIDE.md → Risk Management |
| Testing | Running tests | COMPREHENSIVE_GUIDE.md → Testing |
| Deployment | Docker deploy | COMPREHENSIVE_GUIDE.md → Deployment |
| Troubleshooting | Issues & fixes | COMPREHENSIVE_GUIDE.md → Troubleshooting |
| API Reference | Function details | DEVELOPMENT_REFERENCE.md → API Reference |
| Development Setup | Local environment | DEVELOPMENT_REFERENCE.md → Development Setup |
| Code Patterns | Architecture patterns | DEVELOPMENT_REFERENCE.md → Architecture Patterns |
| Testing Patterns | Test strategies | DEVELOPMENT_REFERENCE.md → Testing Strategies |
| Optimization | Performance tuning | DEVELOPMENT_REFERENCE.md → Performance & Optimization |
| Extending System | Adding features | DEVELOPMENT_REFERENCE.md → Extending the System |
| Common Errors | Debugging | DEVELOPMENT_REFERENCE.md → Common Gotchas |
| Logging | Debugging & logs | DEVELOPMENT_REFERENCE.md → Debugging & Logging |

---

## 📍 By User Type

### New User
1. README.md (5 min)
2. COMPREHENSIVE_GUIDE.md → Quick Start section
3. COMPREHENSIVE_GUIDE.md → Web UI Features section

### System Administrator / Operations
1. COMPREHENSIVE_GUIDE.md → Deployment section
2. COMPREHENSIVE_GUIDE.md → Risk Management section
3. COMPREHENSIVE_GUIDE.md → Troubleshooting section

### Developer / Contributor
1. DEVELOPMENT_REFERENCE.md → Development Setup
2. DEVELOPMENT_REFERENCE.md → Architecture Patterns
3. COMPREHENSIVE_GUIDE.md → Testing section
4. DEVELOPMENT_REFERENCE.md → API Reference

### QA / Tester
1. COMPREHENSIVE_GUIDE.md → Web UI Features
2. COMPREHENSIVE_GUIDE.md → Testing section
3. DEVELOPMENT_REFERENCE.md → Testing Strategies

### DevOps / Infrastructure
1. COMPREHENSIVE_GUIDE.md → Deployment section
2. COMPREHENSIVE_GUIDE.md → Troubleshooting section
3. DEVELOPMENT_REFERENCE.md → Performance section

---

## 🚨 Problem Solver

### "Something's not working!"
1. COMPREHENSIVE_GUIDE.md → Troubleshooting section
   - Portfolio not loading?
   - Web UI not accessible?
   - API connection errors?
   - Test failures?

2. DEVELOPMENT_REFERENCE.md → Common Gotchas section
   - Import errors?
   - Database locking?
   - Async issues?
   - ORM problems?

3. DEVELOPMENT_REFERENCE.md → Debugging & Logging
   - How to view logs?
   - How to debug?
   - Database queries?

### "How do I...?"
- **...start the system?** → README.md
- **...use the web UI?** → COMPREHENSIVE_GUIDE.md (Web UI Features)
- **...trade via CLI?** → COMPREHENSIVE_GUIDE.md (CLI section)
- **...test my changes?** → DEVELOPMENT_REFERENCE.md (Testing Strategies)
- **...deploy to production?** → COMPREHENSIVE_GUIDE.md (Deployment)
- **...add a new strategy?** → DEVELOPMENT_REFERENCE.md (Extending System)
- **...debug an issue?** → DEVELOPMENT_REFERENCE.md (Debugging & Logging)
- **...optimize performance?** → DEVELOPMENT_REFERENCE.md (Performance section)

---

## 📑 File Structure

```
Root (Start here):
├── README.md                          ← QUICKSTART (5 min)
├── COMPREHENSIVE_GUIDE.md             ← COMPLETE GUIDE (everything)
├── DEVELOPMENT_REFERENCE.md           ← DEVELOPER GUIDE (code patterns)
└── DOCUMENTATION_CONSOLIDATION_COMPLETE.md  ← Summary of consolidation

docs/:
├── CONSOLIDATION_INDEX.md             ← File mapping reference
└── archived/                           ← Historical files (for reference only)
    ├── ASYNC_OPTIMIZATION.md          (content in DEVELOPMENT_REFERENCE.md)
    ├── TESTING_GUIDE.md               (content in COMPREHENSIVE_GUIDE.md)
    ├── QUICK_WINS_*.md                (content in COMPREHENSIVE_GUIDE.md)
    └── ... (6 more archived files)

Package level (unchanged):
├── binance_trade_agent/README.md      ← Package-specific docs
└── .github/copilot-instructions.md    ← AI integration guide
```

---

## ⚡ Quick Commands

```bash
# Start system
./deploy.sh development
# Then: http://localhost:8501

# Run tests
docker-compose exec trading-agent pytest -v

# Check container status
docker-compose ps

# View logs
docker-compose logs -f

# Access shell
docker-compose exec trading-agent /bin/bash

# For full command reference
# See: COMPREHENSIVE_GUIDE.md → Quick Command Reference
```

---

## 🎓 Reading Order Recommendations

### Path 1: New User (90 minutes)
1. README.md (5 min)
2. COMPREHENSIVE_GUIDE.md → Quick Start (10 min)
3. COMPREHENSIVE_GUIDE.md → Architecture (10 min)
4. COMPREHENSIVE_GUIDE.md → Installation (5 min)
5. COMPREHENSIVE_GUIDE.md → Web UI Features (20 min, play with UI)
6. COMPREHENSIVE_GUIDE.md → Usage Guides (30 min)

### Path 2: Developer (2-3 hours)
1. DEVELOPMENT_REFERENCE.md → Development Setup (15 min)
2. DEVELOPMENT_REFERENCE.md → Architecture Patterns (30 min)
3. DEVELOPMENT_REFERENCE.md → API Reference (30 min, reference while coding)
4. DEVELOPMENT_REFERENCE.md → Testing Strategies (20 min)
5. COMPREHENSIVE_GUIDE.md → Testing section (15 min)
6. DEVELOPMENT_REFERENCE.md → Common Gotchas (20 min)

### Path 3: Operations/Deployment (1 hour)
1. README.md (5 min)
2. COMPREHENSIVE_GUIDE.md → Installation (10 min)
3. COMPREHENSIVE_GUIDE.md → Deployment (20 min)
4. COMPREHENSIVE_GUIDE.md → Risk Management (15 min)
5. COMPREHENSIVE_GUIDE.md → Troubleshooting (10 min)

---

## 🔖 Bookmarks to Save

```
MUST BOOKMARK:
1. README.md - For new people & quick reference
2. COMPREHENSIVE_GUIDE.md - Most comprehensive
3. DEVELOPMENT_REFERENCE.md - If you develop code

OPTIONAL:
4. docs/CONSOLIDATION_INDEX.md - If curious about file mapping
5. DOCUMENTATION_CONSOLIDATION_COMPLETE.md - Summary of consolidation
```

---

## 💡 Pro Tips

- **Ctrl+F** in your browser/editor to search within documents
- **README.md** has a "Table of Contents" - use to jump to sections
- **COMPREHENSIVE_GUIDE.md** has detailed "Table of Contents"
- **DEVELOPMENT_REFERENCE.md** is organized by topic - easy to find what you need
- **Each section** has examples you can copy/paste
- **Quick Command Reference** at end of COMPREHENSIVE_GUIDE.md for common commands

---

**Status:** ✅ Documentation is consolidated, organized, and ready to use!

**Last Updated:** November 9, 2025  
**Keep this card handy!**
