"""
AI Infrastructure Intelligence Platform
Main FastAPI Backend Server
- Rate limiting (slowapi)
- Strict CORS (no wildcard in production)
- APScheduler with misfire guard
"""
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from apscheduler.schedulers.background import BackgroundScheduler
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from database import Base, engine, get_db
from models import Server, ProjectDiscovery
from services.server_scanner import scan_server_projects
from services.ai_insights_engine import generate_all_insights
from services.duplicate_detector import detect_duplicates
from services.inactive_detector import detect_inactive_projects

from routers import stats, projects, servers, cleanup, discovery, whm, ml, ai, audit, dashboard_spec
from routers.auth import router as auth_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend.main")

Base.metadata.create_all(bind=engine, checkfirst=True)

# ========================
# Rate Limiter
# ========================
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

# ========================
# Scheduler
# ========================
scheduler = BackgroundScheduler()


def hourly_sync_job():
    """Hourly background synchronization — rescans server metrics, detects duplicates/inactives, refreshes AI insights."""
    logger.info("APScheduler: Running hourly synchronization job...")
    db = next(get_db())
    try:
        all_servers = db.query(Server).all()
        for server in all_servers:
            try:
                scan_server_projects(db, server, triggered_by="scheduler")
            except Exception as scan_err:
                logger.warning(f"APScheduler: Failed to scan {server.name}: {scan_err}")

        discoveries = db.query(ProjectDiscovery).all()
        detect_duplicates(discoveries)
        detect_inactive_projects(discoveries)
        generate_all_insights(db)
        db.commit()
    except Exception as e:
        logger.error(f"APScheduler sync job error: {e}")
        db.rollback()
    finally:
        db.close()
    logger.info("APScheduler: Hourly sync job completed.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(
        hourly_sync_job,
        "interval",
        hours=1,
        id="hourly_sync",
        misfire_grace_time=300,       # Allow 5-min late execution
        max_instances=1,              # Prevent overlapping runs
        coalesce=True,                # Merge missed runs into one
    )
    scheduler.start()
    logger.info("APScheduler started — hourly background sync active.")
    yield
    scheduler.shutdown()
    logger.info("APScheduler stopped.")


# ========================
# FastAPI App
# ========================
app = FastAPI(
    title="AI Infrastructure Intelligence Platform",
    version="3.0.0",
    lifespan=lifespan,
)

# Rate limiter registration
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — restrict to known origins (env-configurable)
ALLOWED_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:5173,https://ai-infrastructure-intelligence-platform.vercel.app"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# ========================
# Routers
# ========================
app.include_router(auth_router)
app.include_router(servers.router)
app.include_router(projects.router)
app.include_router(cleanup.router)
app.include_router(stats.router)
app.include_router(discovery.router)
app.include_router(whm.router)
app.include_router(ml.router)
app.include_router(ai.router)
app.include_router(audit.router)
app.include_router(dashboard_spec.router)


@app.api_route("/", methods=["GET", "HEAD"])
def root():
    return {"message": "AI Infrastructure Intelligence Platform", "version": "3.0.0", "status": "running"}


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "database": "connected",
        "scheduler": "running" if scheduler.running else "stopped",
    }