#!/bin/bash
# Binance Testnet Test Runner
# This script starts the app configured for Binance testnet

echo "=========================================="
echo "Binance Trading Agent - Testnet Test Run"
echo "=========================================="
echo ""

# Check for API credentials
if [ -z "$BINANCE_API_KEY" ] || [ -z "$BINANCE_API_SECRET" ]; then
    echo "⚠️  WARNING: No Binance API credentials detected."
    echo ""
    echo "To test against Binance Testnet, you need:"
    echo "1. Create a testnet account at: https://testnet.binance.vision/"
    echo "2. Generate API key and secret"
    echo "3. Set environment variables:"
    echo "   export BINANCE_API_KEY='your_testnet_key'"
    echo "   export BINANCE_API_SECRET='your_testnet_secret'"
    echo ""
    echo "Running in DEMO MODE with mock data..."
    echo ""
else
    echo "✅ API credentials detected"
    echo "🔧 Configuring for Binance Testnet"
    echo ""
fi

# Set configuration
export BINANCE_TESTNET=true
export DEMO_MODE=false
export LOG_LEVEL=DEBUG

echo "Starting Binance Trading Agent..."
echo ""

# Start the API server
python -m binance_trade_agent.api.api
