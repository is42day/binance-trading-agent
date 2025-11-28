# Start automated trading agent in Docker background

# Usage:
#   .\start_trading_bg.ps1                                    # Default: combined strategy
#   .\start_trading_bg.ps1 -Strategy rsi -Interval 30         # RSI every 30s
#   .\start_trading_bg.ps1 -Symbols "BTCUSDT,ETHUSDT" -Strategy macd

param(
    [string]$Strategy = "combined",
    [string]$Symbols = "BTCUSDT",
    [int]$Interval = 60,
    [switch]$Stop = $false,
    [switch]$Logs = $false
)

if ($Stop) {
    Write-Host "Stopping trading agent..." -ForegroundColor Yellow
    docker stop trading-agent 2>$null
    Write-Host "Stopped" -ForegroundColor Green
    exit 0
}

if ($Logs) {
    Write-Host "Trading Agent Logs:" -ForegroundColor Cyan
    docker logs -f trading-agent
    exit 0
}

Write-Host ""
Write-Host "=== Automated Trading Agent ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Strategy:  $Strategy" -ForegroundColor Green
Write-Host "Symbols:   $Symbols" -ForegroundColor Green
Write-Host "Interval:  ${Interval}s" -ForegroundColor Green
Write-Host ""

# Stop any existing trading agent
docker stop trading-agent 2>$null

# Start new trading agent
Write-Host "Starting trading agent..." -ForegroundColor Cyan
docker run -d `
    --name trading-agent `
    --env-file .env `
    -v "$(pwd)/logs:/app/logs" `
    -v "$(pwd)/data:/app/data" `
    binance-trading-agent:latest `
    python start_auto_trading.py `
    --strategy $Strategy `
    --symbols $Symbols `
    --interval $Interval

if ($LASTEXITCODE -eq 0) {
    Write-Host "Agent started successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Commands:" -ForegroundColor Cyan
    Write-Host "  View logs:  .\start_trading_bg.ps1 -Logs" -ForegroundColor Yellow
    Write-Host "  Stop:       .\start_trading_bg.ps1 -Stop" -ForegroundColor Yellow
    Write-Host "  Check:      docker ps | findstr trading-agent" -ForegroundColor Yellow
} else {
    Write-Host "Failed to start agent" -ForegroundColor Red
    exit 1
}
