import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from priotag.api.routes import (
    account,
    admin,
    auth,
    health,
    institutions,
    priorities,
    vacation_days,
)
from priotag.config import settings
from priotag.logging_config import setup_logging
from priotag.middleware.metrics import (
    PrometheusMetricsMiddleware,
    metrics_endpoint,
    track_csp_violation,
)
from priotag.middleware.security_headers import SecurityHeadersMiddleware
from priotag.services.redis_service import close_redis, redis_health_check
from priotag.static_files_utils import setup_static_file_serving

ENV = os.getenv("ENV", "production")
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG" if ENV == "development" else "INFO")
SERVE_STATIC = os.getenv("SERVE_STATIC", "false").lower() == "true"
setup_logging(LOG_LEVEL)


logger = logging.getLogger(__name__)
logger.info("Starting PrioTag API")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _ = app  # remove unused warning
    _ = asyncio  # remove unused warning
    # Startup: test Redis connection
    if not redis_health_check():
        raise RuntimeError("Failed to connect to Redis")
    print("✓ Redis connected")

    yield

    # Shutdown: close connections
    close_redis()
    print("✓ Redis connections closed")


# Create FastAPI app
app = FastAPI(
    title="PrioTag API",
    description="API for analyzing images and PDFs with Excel output generation",
    version="0.1.0",
    docs_url=None if ENV == "production" else "/api/docs",
    redoc_url=None if ENV == "production" else "/api/redoc",
    lifespan=lifespan,
)


# CORS configuration
if ENV == "development":
    # In development, allow frontend dev server
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",  # Vite dev server
            "http://localhost:5174",  # Vite dev server
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # Production CORS
    allowed_origins = os.getenv("CORS_ORIGINS", "").split(",")
    if allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["*"],
        )

static_path = Path("/app/static")

app.add_middleware(PrometheusMetricsMiddleware)

app.add_middleware(
    SecurityHeadersMiddleware,
    static_path=static_path,
    enable_hsts=(ENV == "production"),
    csp_report_uri="/api/csp-violations",
)

# API routes
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(priorities.router, prefix="/api/v1/priorities", tags=["Prioliste"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Pocketbase"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(institutions.router, prefix="/api/v1", tags=["Institutions"])
app.include_router(
    vacation_days.router, prefix="/api/v1/admin", tags=["Vacation Days Admin"]
)
app.include_router(vacation_days.user_router, prefix="/api/v1", tags=["Vacation Days"])
app.include_router(account.router, prefix="/api/v1/account", tags=["Account"])


@app.post("/api/csp-violations")
async def csp_violation_report(request: Request):
    report = await request.json()
    violated_directive = report.get("violated-directive", "unknown")
    if violated_directive:
        directive = violated_directive.split()[0] if violated_directive else "unknown"
        track_csp_violation(directive)
    logger.warning(f"CSP Violation: {report}")
    return {"status": "ok"}


metrics_token_file = Path("/run/secrets/metrics_token")
if not metrics_token_file.exists():
    logger.warning("Missing metrics token file")
else:
    METRICS_TOKEN = metrics_token_file.read_text().strip()

security = HTTPBearer()


@app.get("/api/v1/metrics")
async def metrics(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Prometheus metrics endpoint"""
    if credentials.credentials != METRICS_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid metrics token"
        )
    return await metrics_endpoint()


# Serve static files in production OR when explicitly enabled in development
setup_static_file_serving(
    app=app, static_path=static_path, env=ENV, serve_static=SERVE_STATIC
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "priotag.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENV == "development",
    )
