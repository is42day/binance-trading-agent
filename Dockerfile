FROM python:3.10-slim

WORKDIR /app

# Install OS-level dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    unzip \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy and install MCP server setup script
RUN pip install --upgrade pip && pip install mcp-server-git

# Copy Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Ensure pytest is installed for testing
RUN pip install pytest

# Copy rest of your application code
COPY . .

# Expose MCP server port (change as needed, default 8080)
EXPOSE 8080

# Start both MCP server and Python app using supervisord
RUN pip install supervisor
COPY supervisord.conf /app/supervisord.conf

CMD ["supervisord", "-c", "/app/supervisord.conf"]
