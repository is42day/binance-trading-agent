#!/bin/bash
set -e

# Install MCP server (Python version)
pip install --upgrade pip
pip install mcp-server-git

# Run MCP server (default port 8080)
mcp-server --host 0.0.0.0 --port 8080
