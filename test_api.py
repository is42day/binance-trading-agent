#!/usr/bin/env python
"""Simple test API to verify FastAPI works."""
from fastapi import FastAPI
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.get("/")
def read_root():
    logger.info("Root endpoint called")
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "message": "Test API is running."
    }

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting test API...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
