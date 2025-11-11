#!/usr/bin/env python
"""
Dash Dashboard Startup Script
Initializes and runs the Binance Trading Agent Dash application
"""

import sys
import os
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_dependencies():
    """Verify all required dependencies are installed"""
    logger.info("Checking dependencies...")
    
    required_packages = {
        'dash': 'Dash',
        'dash_bootstrap_components': 'Dash Bootstrap Components',
        'plotly': 'Plotly',
        'pandas': 'Pandas',
        'requests': 'Requests'
    }
    
    missing = []
    for module, name in required_packages.items():
        try:
            __import__(module)
            logger.info(f"  ✓ {name}")
        except ImportError:
            logger.error(f"  ✗ {name} (missing)")
            missing.append(module)
    
    if missing:
        logger.error(f"\nMissing packages: {', '.join(missing)}")
        logger.error("Install with: pip install -r binance_trade_agent/dashboard/requirements.txt")
        return False
    
    logger.info("All dependencies available ✓")
    return True


def check_css_assets():
    """Verify CSS files are in place"""
    logger.info("Checking CSS assets...")
    
    css_file = Path(__file__).parent / 'assets' / 'style.css'
    if css_file.exists():
        size_kb = css_file.stat().st_size / 1024
        logger.info(f"  ✓ style.css ({size_kb:.1f} KB)")
        return True
    else:
        logger.error(f"  ✗ style.css not found at {css_file}")
        return False


def check_data_directory():
    """Verify data directory exists and is writable"""
    logger.info("Checking data directory...")
    
    data_dir = Path('/app/data')
    
    # For local development, also check current directory
    if not data_dir.exists():
        data_dir = Path('./data')
        if not data_dir.exists():
            logger.warning(f"  ⚠ Data directory not found, creating {data_dir}")
            data_dir.mkdir(parents=True, exist_ok=True)
    
    if data_dir.is_dir():
        logger.info(f"  ✓ Data directory: {data_dir}")
        return True
    else:
        logger.error(f"  ✗ Data directory not accessible: {data_dir}")
        return False


def check_component_imports():
    """Verify all dashboard modules can be imported"""
    logger.info("Checking dashboard module imports...")
    
    try:
        logger.info("  Importing data_fetch...")
        from binance_trade_agent.dashboard.utils import data_fetch
        logger.info("    ✓ data_fetch")
        
        logger.info("  Importing components.navbar...")
        from binance_trade_agent.dashboard.components import navbar
        logger.info("    ✓ navbar")
        
        logger.info("  Importing pages...")
        from binance_trade_agent.dashboard.pages import (
            portfolio, market_data, signals_risk, execute_trade,
            system_health, logs, advanced
        )
        logger.info("    ✓ portfolio, market_data, signals_risk, execute_trade")
        logger.info("    ✓ system_health, logs, advanced")
        
        return True
    except ImportError as e:
        logger.error(f"  ✗ Import error: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"  ✗ Unexpected error: {str(e)}")
        return False


def initialize_app():
    """Initialize Dash app and verify components"""
    logger.info("Initializing Dash app...")
    
    try:
        import dash
        import dash_bootstrap_components as dbc
        
        # Import main app
        from binance_trade_agent.dashboard.app import app
        
        logger.info("  ✓ App initialized")
        logger.info(f"  ✓ Server: {app.server}")
        logger.info(f"  ✓ Layout ready")
        
        return app
    except Exception as e:
        logger.error(f"  ✗ Failed to initialize app: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main startup routine"""
    logger.info("=" * 60)
    logger.info("Binance Trading Agent - Dash Dashboard")
    logger.info("=" * 60)
    
    # Run checks
    checks = [
        check_dependencies(),
        check_css_assets(),
        check_data_directory(),
        check_component_imports(),
    ]
    
    if not all(checks):
        logger.error("\n❌ Pre-flight checks failed!")
        return False
    
    logger.info("\n✅ All pre-flight checks passed!")
    
    # Initialize app
    app = initialize_app()
    if not app:
        logger.error("\n❌ Failed to initialize app!")
        return False
    
    logger.info("\n" + "=" * 60)
    logger.info("Starting Dash server...")
    logger.info("=" * 60)
    logger.info("\n🚀 Dashboard available at:")
    logger.info("   http://localhost:8050/")
    logger.info("\n📊 Pages:")
    logger.info("   /                  - Portfolio")
    logger.info("   /market-data       - Market Data")
    logger.info("   /signals-risk      - Signals & Risk")
    logger.info("   /execute-trade     - Execute Trade")
    logger.info("   /system-health     - System Health")
    logger.info("   /logs              - Logs")
    logger.info("   /advanced          - Advanced")
    logger.info("\nPress Ctrl+C to stop")
    logger.info("=" * 60 + "\n")
    
    # Run server
    try:
        app.run(
            host='0.0.0.0',
            port=8050,
            debug=False,
            threaded=True
        )
    except KeyboardInterrupt:
        logger.info("\n\nShutdown signal received")
        logger.info("Dashboard stopped ✓")
        return True
    except Exception as e:
        logger.error(f"\n❌ Server error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
