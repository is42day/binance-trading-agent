# Binance Trading Agent - Testnet Test Runner

param(
    [switch]$Demo = $false,
    [switch]$Help = $false
)

if ($Help) {
    Write-Host ""
    Write-Host "=== Binance Trading Agent - Testnet Test Runner ===" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "USAGE:"
    Write-Host "  .\start_testnet.ps1              # Run with API credentials (testnet)"
    Write-Host "  .\start_testnet.ps1 -Demo       # Run in demo mode with mock data"
    Write-Host ""
    Write-Host "SETUP:"
    Write-Host "1. Get testnet credentials from https://testnet.binance.vision/"
    Write-Host "2. Set environment variables:"
    Write-Host "   `$env:BINANCE_API_KEY = 'your_testnet_key'"
    Write-Host "   `$env:BINANCE_API_SECRET = 'your_testnet_secret'"
    Write-Host "3. Run: .\start_testnet.ps1"
    Write-Host ""
    Write-Host "ACCESS:"
    Write-Host "  API:       http://localhost:8000"
    Write-Host "  Dashboard: http://localhost:8050"
    Write-Host "  Redis:     localhost:6379"
    Write-Host ""
    exit 0
}

Write-Host ""
Write-Host "=== Binance Trading Agent - Testnet Startup ===" -ForegroundColor Cyan
Write-Host ""

# Check/set environment
if ($Demo) {
    Write-Host "Running in DEMO MODE (mock data)" -ForegroundColor Green
    $env:BINANCE_TESTNET = 'true'
    $env:DEMO_MODE = 'true'
} else {
    Write-Host "Running in TESTNET MODE" -ForegroundColor Green
    
    if (-not $env:BINANCE_API_KEY -or -not $env:BINANCE_API_SECRET) {
        Write-Host "WARNING: No API credentials found" -ForegroundColor Yellow
        Write-Host "Using DEMO MODE instead" -ForegroundColor Yellow
        $env:DEMO_MODE = 'true'
    } else {
        Write-Host "API credentials detected" -ForegroundColor Green
        $env:BINANCE_TESTNET = 'true'
        $env:DEMO_MODE = 'false'
    }
}

Write-Host ""
Write-Host "Building Docker image..." -ForegroundColor Cyan
docker build -t binance-trading-agent:latest . -q

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Build failed" -ForegroundColor Red
    exit 1
}

Write-Host "Starting services..." -ForegroundColor Cyan
docker-compose up -d --remove-orphans

Write-Host "Waiting for services..." -ForegroundColor Cyan
Start-Sleep -Seconds 3

Write-Host ""
Write-Host "=== READY FOR TESTING ===" -ForegroundColor Green
Write-Host ""
Write-Host "API Server:   http://localhost:8000" -ForegroundColor Yellow
Write-Host "Dashboard:    http://localhost:8050" -ForegroundColor Yellow
Write-Host ""
Write-Host "Test with:"
Write-Host "  curl http://localhost:8000/"
Write-Host "  curl http://localhost:8000/api/v1/portfolio/summary"
Write-Host ""
Write-Host "Stop with:   docker-compose down"
Write-Host ""
