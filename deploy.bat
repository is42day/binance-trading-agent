@echo off
REM Binance Trading Agent Deployment Script for Windows
REM Usage: deploy.bat [development|production|monitoring]

setlocal enabledelayedexpansion

set "RED=[91m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "NC=[0m"

REM Functions (using labels)
goto :main

:log_info
echo %BLUE%[INFO]%NC% %~1
exit /b

:log_success
echo %GREEN%[SUCCESS]%NC% %~1
exit /b

:log_warning
echo %YELLOW%[WARNING]%NC% %~1
exit /b

:log_error
echo %RED%[ERROR]%NC% %~1
exit /b

:check_docker
where docker >nul 2>nul
if errorlevel 1 (
    call :log_error "Docker is not installed. Please install Docker Desktop first."
    exit /b 1
)

where docker-compose >nul 2>nul
if errorlevel 1 (
    call :log_error "Docker Compose is not installed. Please install Docker Compose first."
    exit /b 1
)

call :log_success "Docker and Docker Compose are available"
exit /b

:check_env
if not exist ".env" (
    if exist ".env.example" (
        call :log_warning ".env file not found. Copying from .env.example"
        copy ".env.example" ".env"
        call :log_warning "Please edit .env file with your actual API keys before running again"
        exit /b 1
    ) else (
        call :log_error ".env file not found and no .env.example available"
        exit /b 1
    )
)
call :log_success "Environment file found"
exit /b

:create_directories
call :log_info "Creating necessary directories..."
if not exist "data" mkdir data
if not exist "logs" mkdir logs
if not exist "monitoring" mkdir monitoring
if not exist "monitoring\grafana" mkdir monitoring\grafana
if not exist "monitoring\grafana\provisioning" mkdir monitoring\grafana\provisioning
call :log_success "Directories created"
exit /b

:deploy_development
call :log_info "Deploying in development mode..."
docker-compose down
docker-compose up --build -d trading-agent
call :log_success "Development deployment completed"
call :log_info "Trading agent is running on http://localhost:8080"
call :log_info "View logs with: docker-compose logs -f trading-agent"
exit /b

:deploy_production
call :log_info "Deploying in production mode..."
docker-compose down
docker-compose build --no-cache trading-agent
docker-compose up -d trading-agent
call :log_success "Production deployment completed"
call :log_info "Trading agent is running on http://localhost:8080"
call :log_info "Health check: http://localhost:8080/health"
exit /b

:deploy_monitoring
call :log_info "Deploying with monitoring stack..."

REM Create Prometheus config if it doesn't exist
if not exist "monitoring\prometheus.yml" (
    call :log_info "Creating Prometheus configuration..."
    (
        echo global:
        echo   scrape_interval: 15s
        echo   evaluation_interval: 15s
        echo.
        echo scrape_configs:
        echo   - job_name: 'trading-agent'
        echo     static_configs:
        echo       - targets: ['trading-agent:9090']
        echo     scrape_interval: 5s
        echo     metrics_path: /metrics
    ) > monitoring\prometheus.yml
)

docker-compose --profile monitoring down
docker-compose --profile monitoring up --build -d
call :log_success "Monitoring deployment completed"
call :log_info "Trading agent: http://localhost:8080"
call :log_info "Prometheus: http://localhost:9091"
call :log_info "Grafana: http://localhost:3000 (admin/admin123)"
exit /b

:show_status
call :log_info "Container status:"
docker-compose ps

echo.
call :log_info "Service endpoints:"
echo   Trading Agent: http://localhost:8080
echo   Health Check:  http://localhost:8080/health

docker-compose ps | find "prometheus" >nul
if not errorlevel 1 (
    echo   Prometheus:    http://localhost:9091
)

docker-compose ps | find "grafana" >nul
if not errorlevel 1 (
    echo   Grafana:       http://localhost:3000
)
exit /b

:show_logs
docker-compose logs -f trading-agent
exit /b

:stop_services
call :log_info "Stopping services..."
docker-compose --profile monitoring down
call :log_success "All services stopped"
exit /b

:cleanup
call :log_info "Cleaning up containers and images..."
docker-compose --profile monitoring down -v
docker system prune -f
call :log_success "Cleanup completed"
exit /b

:run_tests
call :log_info "Running tests..."
docker-compose exec trading-agent python -m pytest binance_trade_agent/tests/ -v
exit /b

:main
echo %BLUE%========================================%NC%
echo %BLUE%  Binance Trading Agent Deployment     %NC%
echo %BLUE%========================================%NC%

call :check_docker
if errorlevel 1 exit /b 1

call :check_env
if errorlevel 1 exit /b 1

call :create_directories

set "command=%~1"
if "%command%"=="" set "command=development"

if "%command%"=="development" goto :deploy_development
if "%command%"=="dev" goto :deploy_development
if "%command%"=="production" goto :deploy_production
if "%command%"=="prod" goto :deploy_production
if "%command%"=="monitoring" goto :deploy_monitoring
if "%command%"=="mon" goto :deploy_monitoring
if "%command%"=="status" goto :show_status
if "%command%"=="logs" goto :show_logs
if "%command%"=="stop" goto :stop_services
if "%command%"=="cleanup" goto :cleanup
if "%command%"=="test" goto :run_tests

echo Usage: %0 [development^|production^|monitoring^|status^|logs^|stop^|cleanup^|test]
echo.
echo Commands:
echo   development  - Deploy in development mode (default)
echo   production   - Deploy in production mode
echo   monitoring   - Deploy with monitoring stack (Prometheus + Grafana)
echo   status       - Show container status
echo   logs         - Show trading agent logs
echo   stop         - Stop all services
echo   cleanup      - Stop services and clean up containers
echo   test         - Run tests in container
exit /b 1