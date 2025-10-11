FROM python:3.10-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

FROM python:3.10-slim AS production

# Create non-root user for security
RUN groupadd -r trading && useradd -r -g trading trading

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install supervisor for process management
RUN pip install supervisor

# Set working directory
WORKDIR /app

# Create data directory for SQLite databases
RUN mkdir -p /app/data && chown trading:trading /app/data

# Copy application code
COPY --chown=trading:trading . .

# Copy configuration files
COPY --chown=trading:trading supervisord.conf /app/supervisord.conf

# Create logs directory
RUN mkdir -p /app/logs && chown trading:trading /app/logs

# Pre-create supervisord log file and set permissions
RUN touch /app/supervisord.log && chown trading:trading /app/supervisord.log && chmod 666 /app/supervisord.log

# Expose ports
EXPOSE 8080 9090 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# Switch to non-root user
USER trading

# Set environment variables
ENV PYTHONPATH=/app
ENV BINANCE_API_URL=https://testnet.binance.vision
ENV MCP_SERVER_PORT=8080
ENV LOG_LEVEL=INFO

# Default command
CMD ["supervisord", "-c", "/app/supervisord.conf"]
