#!/usr/bin/env python3
"""
MathLab University - Backend Entry Point (FastAPI)
"""
import os
import uvicorn
from app import app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    
    uvicorn.run(
        "app:app",
        host=host,
        port=port,
        reload=False,  # True seulement en dev
        log_level="info"
    )