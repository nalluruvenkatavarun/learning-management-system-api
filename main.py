from fastapi import FastAPI, HTTPException
from fastapi.openapi.utils import get_openapi
from fastapi.security import HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from routes import router
from middleware import limiter, rate_limit_exceeded_handler, InputValidationMiddleware, SecurityHeadersMiddleware
from slowapi.errors import RateLimitExceeded
import os
import logging
from database import database
from dotenv import load_dotenv
from contextlib import asynccontextmanager

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create security scheme
security = HTTPBearer()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up LMS API...")
    yield
    # Shutdown
    logger.info("Shutting down LMS API...")

# Environment configuration
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

app = FastAPI(
    title="Learning Management System", 
    version="1.0.0",
    description="A production-ready Learning Management System API",
    debug=DEBUG,
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "Authentication",
            "description": "User authentication endpoints"
        },
        {
            "name": "Courses",
            "description": "Course management endpoints"
        },
        {
            "name": "Lessons",
            "description": "Lesson management endpoints"
        },
        {
            "name": "Quizzes",
            "description": "Quiz management endpoints"
        },
        {
            "name": "Progress",
            "description": "Progress tracking endpoints"
        }
    ]
)

# Configure OpenAPI with security schemes
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Learning Management System",
        version="1.0.0",
        description="A comprehensive Learning Management System API with authentication",
        routes=app.routes,
    )
    
    # Add security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    
    # Add security requirements to protected endpoints
    protected_endpoints = [
        "/create_course",
        "/courses/{course_id}/enroll",
        "/courses/{course_id}/lessons",
        "/courses/{course_id}/quizzes",
        "/quizzes/{quiz_id}/questions",
        "/lessons/{lesson_id}/complete",
        "/quizzes/{quiz_id}/attempt",
        "/quizzes/{quiz_id}/attempts",
        "/courses/{course_id}/progress"
    ]
    
    for path in openapi_schema["paths"]:
        for method in openapi_schema["paths"][path]:
            operation = openapi_schema["paths"][path][method]
            # Add security requirement for protected endpoints
            if path in protected_endpoints:
                operation["security"] = [{"BearerAuth": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Add CORS middleware
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Add input validation middleware
app.add_middleware(InputValidationMiddleware)

# Add trusted host middleware for production
if ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]  # Configure with your actual domain in production
    )

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Include all routes
app.include_router(router)

@app.get("/")
def read_root():
    return {"message": "Welcome to Learning Management System API"}

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Test database connection
        await database.command("ping")
        return {
            "status": "healthy",
            "database": "connected",
            "environment": ENVIRONMENT
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8864"))
    uvicorn.run("main:app", host=host, port=port, reload=True) 