"""
Main FastAPI application entry point.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import os

from app.config import settings
from app.models.database import init_db, close_db
from app.api.routes import scraper, jobs, exports, auth, products
# Add to imports
from app.api.routes import scraper, jobs, exports, auth, websocket, products

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting up E-Commerce Scraper Platform...")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Create export directory
    os.makedirs(settings.EXPORT_PATH, exist_ok=True)
    
    # Install Playwright browsers
    try:
        from playwright.async_api import async_playwright
        logger.info("Playwright ready")
    except Exception as e:
        logger.warning(f"Playwright initialization warning: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down E-Commerce Scraper Platform...")
    await close_db()
    logger.info("Database connections closed")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="""
    ## E-Commerce Web Scraping Platform
    
    A comprehensive solution for extracting product data from any e-commerce website.
    
    ### Features:
    * 🔍 Auto-detect product listings and details
    * 📦 Extract complete product information
    * 📊 Handle pagination automatically
    * 🔄 Support for multiple e-commerce platforms
    * 📁 Export to CSV, Excel, JSON
    * 📈 Real-time progress tracking
    """,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)


# Parse ALLOWED_ORIGINS from settings string
def _parse_origins(raw: str) -> list:
    raw = raw.strip()
    if raw == "*":
        return ["*"]
    if raw.startswith("["):
        import json
        return json.loads(raw)
    return [o.strip() for o in raw.split(",") if o.strip()]

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_origins(settings.ALLOWED_ORIGINS),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time to response headers."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "An unexpected error occurred",
            "detail": str(exc) if settings.DEBUG else None
        }
    )


# Include routers
app.include_router(
    scraper.router,
    prefix=f"{settings.API_PREFIX}/scraper",
    tags=["Scraper"]
)

app.include_router(
    jobs.router,
    prefix=f"{settings.API_PREFIX}/jobs",
    tags=["Jobs"]
)

app.include_router(
    exports.router,
    prefix=f"{settings.API_PREFIX}/exports",
    tags=["Exports"]
)

app.include_router(
    auth.router,
    prefix=f"{settings.API_PREFIX}/auth",
    tags=["Authentication"]
)

app.include_router(
    products.router,
    prefix=f"{settings.API_PREFIX}/products",
    tags=["Products"]
)

# Add WebSocket router (add after other routers)
app.include_router(
    websocket.router,
    prefix=f"{settings.API_PREFIX}",
    tags=["WebSocket"]
)

# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Welcome to E-Commerce Scraper Platform",
        "version": settings.APP_VERSION,
        "docs": "/api/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )