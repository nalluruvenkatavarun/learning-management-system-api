from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import os
import logging
from typing import Optional
import re

logger = logging.getLogger(__name__)

# Rate limiter configuration
limiter = Limiter(key_func=get_remote_address)

# Get rate limit from environment variable
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

def get_rate_limit():
    """Get rate limit per minute from environment"""
    return f"{RATE_LIMIT_PER_MINUTE}/minute"

def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Custom handler for rate limit exceeded"""
    return Response(
        content={"detail": "Rate limit exceeded. Please try again later."},
        status_code=429,
        media_type="application/json"
    )

class InputValidationMiddleware(BaseHTTPMiddleware):
    """Middleware for basic input validation"""
    
    async def dispatch(self, request: Request, call_next):
        # Validate request path
        if not self._is_valid_path(request.url.path):
            raise HTTPException(status_code=400, detail="Invalid request path")
        
        # Validate content type for POST/PUT requests that have a body
        if request.method in ["POST", "PUT", "PATCH"]:
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > 0:
                content_type = request.headers.get("content-type", "")
                if not content_type.startswith("application/json"):
                    raise HTTPException(status_code=400, detail="Content-Type must be application/json")
        
        # Validate request size (limit to 1MB)
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 1024 * 1024:  # 1MB
            raise HTTPException(status_code=413, detail="Request too large")
        
        response = await call_next(request)
        return response
    
    def _is_valid_path(self, path: str) -> bool:
        """Validate request path format"""
        # Allow alphanumeric, hyphens, underscores, and forward slashes
        return bool(re.match(r'^[a-zA-Z0-9\-_/]+$', path))

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        return response 