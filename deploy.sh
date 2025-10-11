#!/bin/bash

# Binance Trading Agent Deployment Script
# Usage: ./deploy.sh [development|production|monitoring]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    log_success "Docker and Docker Compose are available"
}

# Check environment file
check_env() {
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            log_warning ".env file not found. Copying from .env.example"
            cp .env.example .env
            log_warning "Please edit .env file with your actual API keys before running again"
            exit 1
        else
            log_error ".env file not found and no .env.example available"
            exit 1
        fi
    fi
    log_success "Environment file found"
}

# Create necessary directories
create_directories() {
    log_info "Creating necessary directories..."
    mkdir -p data logs monitoring/grafana/provisioning
    log_success "Directories created"
}

# Build and start services
deploy_development() {
    log_info "Deploying in development mode..."
    
    # Stop existing containers
    docker-compose down
    
    # Build and start
    docker-compose up --build -d trading-agent
    
    log_success "Development deployment completed"
    log_info "Trading agent is running on http://localhost:8080"
    log_info "View logs with: docker-compose logs -f trading-agent"
}

deploy_production() {
    log_info "Deploying in production mode..."
    
    # Stop existing containers
    docker-compose down
    
    # Pull latest images and build
    docker-compose build --no-cache trading-agent
    
    # Start services
    docker-compose up -d trading-agent
    
    log_success "Production deployment completed"
    log_info "Trading agent is running on http://localhost:8080"
    log_info "Health check: http://localhost:8080/health"
}

deploy_monitoring() {
    log_info "Deploying with monitoring stack..."
    
    # Create Prometheus config if it doesn't exist
    if [ ! -f "monitoring/prometheus.yml" ]; then
        log_info "Creating Prometheus configuration..."
        mkdir -p monitoring
        cat > monitoring/prometheus.yml << EOF
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'trading-agent'
    static_configs:
      - targets: ['trading-agent:9090']
    scrape_interval: 5s
    metrics_path: /metrics
EOF
    fi
    
    # Stop existing containers
    docker-compose --profile monitoring down
    
    # Start all services including monitoring
    docker-compose --profile monitoring up --build -d
    
    log_success "Monitoring deployment completed"
    log_info "Trading agent: http://localhost:8080"
    log_info "Prometheus: http://localhost:9091"
    log_info "Grafana: http://localhost:3000 (admin/admin123)"
}

# Show status
show_status() {
    log_info "Container status:"
    docker-compose ps
    
    echo ""
    log_info "Service endpoints:"
    echo "  Trading Agent: http://localhost:8080"
    echo "  Health Check:  http://localhost:8080/health"
    
    if docker-compose ps | grep -q prometheus; then
        echo "  Prometheus:    http://localhost:9091"
    fi
    
    if docker-compose ps | grep -q grafana; then
        echo "  Grafana:       http://localhost:3000"
    fi
}

# Show logs
show_logs() {
    docker-compose logs -f trading-agent
}

# Stop services
stop_services() {
    log_info "Stopping services..."
    docker-compose --profile monitoring down
    log_success "All services stopped"
}

# Clean up
cleanup() {
    log_info "Cleaning up containers and images..."
    docker-compose --profile monitoring down -v
    docker system prune -f
    log_success "Cleanup completed"
}

# Run tests
run_tests() {
    log_info "Running tests..."
    docker-compose exec trading-agent python -m pytest binance_trade_agent/tests/ -v
}

# Main script
main() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Binance Trading Agent Deployment     ${NC}"
    echo -e "${BLUE}========================================${NC}"
    
    check_docker
    check_env
    create_directories
    
    case "${1:-development}" in
        "development" | "dev")
            deploy_development
            ;;
        "production" | "prod")
            deploy_production
            ;;
        "monitoring" | "mon")
            deploy_monitoring
            ;;
        "status")
            show_status
            ;;
        "logs")
            show_logs
            ;;
        "stop")
            stop_services
            ;;
        "cleanup")
            cleanup
            ;;
        "test")
            run_tests
            ;;
        *)
            echo "Usage: $0 [development|production|monitoring|status|logs|stop|cleanup|test]"
            echo ""
            echo "Commands:"
            echo "  development  - Deploy in development mode (default)"
            echo "  production   - Deploy in production mode"
            echo "  monitoring   - Deploy with monitoring stack (Prometheus + Grafana)"
            echo "  status       - Show container status"
            echo "  logs         - Show trading agent logs"
            echo "  stop         - Stop all services"
            echo "  cleanup      - Stop services and clean up containers"
            echo "  test         - Run tests in container"
            exit 1
            ;;
    esac
}

main "$@"