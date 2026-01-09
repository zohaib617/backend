#!/usr/bin/env python3
"""
Production startup script for TodoApp Backend API.

This script starts the FastAPI application using uvicorn with production-appropriate settings.
It reads the PORT environment variable which is commonly used by hosting platforms.
"""

import os
import uvicorn
from src.main import app

def main():
    """
    Main entry point for the application server.

    Reads the PORT environment variable (default: 8000) and starts the uvicorn server.
    Uses production settings appropriate for deployment platforms.
    """
    # Get port from environment variable, default to 8000
    port = int(os.environ.get("PORT", 8000))

    # Get host from environment variable, default to 0.0.0.0 for external access
    host = os.environ.get("HOST", "0.0.0.0")

    # Get reload setting (should be False in production)
    reload = os.environ.get("DEBUG", "False").lower() == "true"

    print(f"Starting TodoApp API server on {host}:{port}")
    print(f"Environment: {os.environ.get('ENVIRONMENT', 'production')}")
    print(f"Debug mode: {reload}")

    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        reload=reload,  # Should be False in production
        log_level="info",
        workers=1,  # For free tier deployments, start with 1 worker
    )

if __name__ == "__main__":
    main()