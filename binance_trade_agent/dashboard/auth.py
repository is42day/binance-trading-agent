"""
Dashboard Authentication Module

Provides HTTP Basic Authentication for the Dash dashboard.
Credentials are configured via environment variables:
- DASHBOARD_USERNAME (default: admin)
- DASHBOARD_PASSWORD (default: changeme)

For production, ALWAYS set strong credentials via environment variables!
"""

import functools
import os
from base64 import b64decode
from typing import Optional, Tuple

from flask import Response, request

# Default credentials - CHANGE THESE IN PRODUCTION via environment variables
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "changeme"


def get_credentials() -> Tuple[str, str]:
    """
    Get authentication credentials from environment variables.
    
    Returns:
        Tuple of (username, password)
    """
    username = os.getenv("DASHBOARD_USERNAME", DEFAULT_USERNAME)
    password = os.getenv("DASHBOARD_PASSWORD", DEFAULT_PASSWORD)
    
    # Warn if using default credentials
    if password == DEFAULT_PASSWORD:
        print(
            "⚠️  WARNING: Using default dashboard password! "
            "Set DASHBOARD_PASSWORD environment variable for production."
        )
    
    return username, password


def check_auth(auth_header: Optional[str]) -> bool:
    """
    Validate Basic Auth header against configured credentials.
    
    Args:
        auth_header: Authorization header value
        
    Returns:
        True if valid, False otherwise
    """
    if not auth_header:
        return False
    
    if not auth_header.startswith("Basic "):
        return False
    
    try:
        # Decode base64 credentials
        encoded = auth_header.split(" ", 1)[1]
        decoded = b64decode(encoded).decode("utf-8")
        
        if ":" not in decoded:
            return False
        
        provided_user, provided_pass = decoded.split(":", 1)
        expected_user, expected_pass = get_credentials()
        
        # Constant-time comparison to prevent timing attacks
        user_ok = provided_user == expected_user
        pass_ok = provided_pass == expected_pass
        
        return user_ok and pass_ok
        
    except Exception:
        return False


def unauthorized_response() -> Response:
    """Create 401 Unauthorized response with WWW-Authenticate header."""
    return Response(
        "Authentication required.\n\nPlease provide valid credentials.",
        status=401,
        headers={"WWW-Authenticate": 'Basic realm="Binance Trading Dashboard"'},
        mimetype="text/plain",
    )


def is_auth_enabled() -> bool:
    """
    Check if authentication is enabled.
    
    Auth can be disabled for development by setting:
    DASHBOARD_AUTH_ENABLED=false
    """
    auth_enabled = os.getenv("DASHBOARD_AUTH_ENABLED", "true").lower()
    return auth_enabled in ("true", "1", "yes", "on")


def require_auth(app):
    """
    Add HTTP Basic Authentication to a Flask/Dash app.
    
    Usage:
        from binance_trade_agent.dashboard.auth import require_auth
        
        app = Dash(__name__)
        require_auth(app)
    
    Args:
        app: Dash application instance
    """
    if not is_auth_enabled():
        print("🔓 Dashboard authentication DISABLED (DASHBOARD_AUTH_ENABLED=false)")
        return
    
    username, _ = get_credentials()
    print(f"🔐 Dashboard authentication ENABLED (username: {username})")
    
    @app.server.before_request
    def check_authentication():
        """Verify authentication on every request."""
        # Skip auth for health check endpoints
        if request.path in ("/health", "/ready", "/_dash-component-suites"):
            return None
        
        # Skip auth for static assets
        if request.path.startswith("/_dash-") or request.path.startswith("/assets/"):
            return None
        
        auth_header = request.headers.get("Authorization")
        
        if not check_auth(auth_header):
            return unauthorized_response()
        
        return None


def protect_route(func):
    """
    Decorator to protect individual routes with Basic Auth.
    
    Usage:
        @app.callback(...)
        @protect_route
        def my_callback(...):
            ...
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if is_auth_enabled():
            auth_header = request.headers.get("Authorization")
            if not check_auth(auth_header):
                return unauthorized_response()
        return func(*args, **kwargs)
    return wrapper
