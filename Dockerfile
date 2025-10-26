# ---------- Build stage ----------
FROM python:3.10-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps for building wheels / optional git pulls
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
  && rm -rf /var/lib/apt/lists/*

# Isolated virtualenv
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Python deps (cached layer)
COPY requirements.txt .
RUN python -m pip install --upgrade pip setuptools wheel --no-cache-dir && \
    pip install --no-cache-dir -r requirements.txt

# ---------- Production stage ----------
FROM python:3.10-slim AS production

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Non-root user
RUN groupadd -r trading && useradd -r -g trading trading

# Bring in virtualenv with ownership set during copy
COPY --from=builder --chown=trading:trading /opt/venv /opt/venv

# Supervisord inside the venv
RUN pip install --no-cache-dir supervisor

# Workdir
WORKDIR /app

# Data dir for SQLite (owned by 'trading')
RUN mkdir -p /app/data /app/logs && chown -R trading:trading /app

# Copy application code (already owned by 'trading')
COPY --chown=trading:trading . .

# Make the package importable for runtime/tests
RUN pip install --no-cache-dir -e .

# Expose ports
EXPOSE 8080 9090 8501

# Runtime env
ENV PYTHONPATH=/app \
    BINANCE_API_URL=https://testnet.binance.vision \
    MCP_SERVER_PORT=8080 \
    LOG_LEVEL=INFO

# Optional healthcheck (Streamlit UI). Comment out if not desired.
# HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
#   CMD python -c "import socket; s=socket.socket(); s.settimeout(3); s.connect(('127.0.0.1', 8501)); s.close()" || exit 1

# Drop privileges
USER trading

# Entrypoint
CMD ["supervisord", "-c", "/app/supervisord.conf"]
