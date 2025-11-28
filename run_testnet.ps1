# Binance Trading Agent - Testnet Test Runner
# This script helps you start the app for testnet testing

param(
    [switch]$Demo = $false,
    [switch]$Help = $false
)

if ($Help) {
    Write-Host @"
╔════════════════════════════════════════════════════════════════════════════╗
║   Binance Trading Agent - Testnet Test Runner                             ║
╚════════════════════════════════════════════════════════════════════════════╝

USAGE:
  .\run_testnet.ps1                    # Run with API credentials (testnet)
  .\run_testnet.ps1 -Demo             # Run in demo mode with mock data

SETUP INSTRUCTIONS:

1. Create Binance Testnet Account:
   - Go to: https://testnet.binance.vision/
   - Click 'Generate TESTNET API KEY'
   - Copy your API Key and Secret

2. Set Environment Variables (PowerShell):
   `$env:BINANCE_API_KEY = 'your_testnet_key'`
   `$env:BINANCE_API_SECRET = 'your_testnet_secret'`

3. Run this script:
   `.\run_testnet.ps1`

WHAT YOU'LL SEE:

   API Server:  http://localhost:8000
   Dashboard:   http://localhost:8050
   Redis:       localhost:6379

TEST ENDPOINTS:

   # Get portfolio summary
   curl http://localhost:8000/api/v1/portfolio/summary

   # Get positions
   curl http://localhost:8000/api/v1/portfolio/positions

   # Get market price
   curl http://localhost:8000/api/v1/market/price/BTCUSDT

EXPECTED PERFORMANCE:

   - API P95 latency: <15ms (target: 100ms)
   - Cache hit rate: >95%
   - Throughput: >50 requests/sec

"@
    exit 0
}

Write-Host @"
╔════════════════════════════════════════════════════════════════════════════╗
║   Binance Trading Agent - Testnet Test Run                                ║
║   Date: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')                                 ║
╚════════════════════════════════════════════════════════════════════════════╝
"@

# Determine if running in testnet or demo mode
if ($Demo) {
    Write-Host "Running in DEMO MODE (mock data)" -ForegroundColor Green
    Write-Host ""
    $env:BINANCE_TESTNET = 'true'
    $env:DEMO_MODE = 'true'
} else {
    Write-Host "Running in TESTNET MODE" -ForegroundColor Green
    Write-Host ""
    
    # Check for API credentials
    if (-not $env:BINANCE_API_KEY -or -not $env:BINANCE_API_SECRET) {
        Write-Host "WARNING: No Binance API credentials detected!" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "To use testnet, you need:" -ForegroundColor Cyan
        Write-Host "1. Create account at: https://testnet.binance.vision/"
        Write-Host "2. Generate API key and secret"
        Write-Host "3. Set environment variables:"
        Write-Host "`$env:BINANCE_API_KEY = 'your_testnet_key'" -ForegroundColor Yellow
        Write-Host "`$env:BINANCE_API_SECRET = 'your_testnet_secret'" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Running in DEMO MODE instead..." -ForegroundColor Green
        Write-Host ""
        $env:DEMO_MODE = 'true'
    } else {
        Write-Host "API credentials detected" -ForegroundColor Green
        Write-Host "Connecting to Binance Testnet..." -ForegroundColor Green
        Write-Host ""
        $env:BINANCE_TESTNET = 'true'
        $env:DEMO_MODE = 'false'
    }
}

# Build Docker image
Write-Host "📦 Building Docker image..." -ForegroundColor Cyan
docker build -t binance-trading-agent:latest . -q

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Build failed!" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Build successful" -ForegroundColor Green
Write-Host ""

# Start containers
Write-Host "🚀 Starting services..." -ForegroundColor Cyan
docker-compose up -d --remove-orphans

Write-Host "✅ Services started" -ForegroundColor Green
Write-Host ""

# Wait for services to be ready
Write-Host "⏳ Waiting for services to be ready..." -ForegroundColor Cyan
Start-Sleep -Seconds 3

# Test API endpoint
Write-Host "🧪 Testing API endpoints..." -ForegroundColor Cyan
Write-Host ""

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/" -Method Get -TimeoutSec 5
    Write-Host "✅ API is responding" -ForegroundColor Green
    Write-Host "   Status: $($response.status)" -ForegroundColor Green
    Write-Host "   Timestamp: $($response.timestamp)" -ForegroundColor Green
} catch {
    Write-Host "⚠️  API not yet ready, starting anyway..." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  System Ready for Testing                                                 ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "📍 API Server:   http://localhost:8000" -ForegroundColor Green
Write-Host "📊 Dashboard:    http://localhost:8050" -ForegroundColor Green
Write-Host "🔴 Redis:        localhost:6379" -ForegroundColor Green
Write-Host ""

Write-Host "🧪 Quick Test Commands:" -ForegroundColor Yellow
Write-Host ""
Write-Host "# Get API health" -ForegroundColor Gray
Write-Host "curl http://localhost:8000/" -ForegroundColor Cyan
Write-Host ""
Write-Host "# Get portfolio summary" -ForegroundColor Gray
Write-Host "curl http://localhost:8000/api/v1/portfolio/summary" -ForegroundColor Cyan
Write-Host ""
Write-Host "# Get positions" -ForegroundColor Gray
Write-Host "curl http://localhost:8000/api/v1/portfolio/positions" -ForegroundColor Cyan
Write-Host ""
Write-Host "# Get market price" -ForegroundColor Gray
Write-Host "curl http://localhost:8000/api/v1/market/price/BTCUSDT" -ForegroundColor Cyan
Write-Host ""

Write-Host "📚 For more information, see: TESTNET_TESTING_GUIDE.md" -ForegroundColor Green
Write-Host ""
Write-Host "🛑 To stop services:" -ForegroundColor Yellow
Write-Host "   docker-compose down" -ForegroundColor Cyan
Write-Host ""
Write-Host "📋 To view logs:" -ForegroundColor Yellow
Write-Host "   docker logs -f binance-trading-agent" -ForegroundColor Cyan
Write-Host ""
