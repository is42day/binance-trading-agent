#!/usr/bin/env python
"""Simple test API to verify FastAPI works."""
import logging
from datetime import datetime

from fastapi import FastAPI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()


@app.get("/")
def read_root():
    logger.info("Root endpoint called")
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "message": "Test API is running.",
    }


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting test API...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
