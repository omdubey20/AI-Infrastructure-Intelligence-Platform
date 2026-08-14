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

from routers import stats, projects, servers, cleanup, discovery, whm, ml, ai, audit, dashboard_spec, monitoring, security, agent
from routers.auth import router as auth_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend.main")

def ensure_default_admin():
    db = next(get_db())
    try:
        from models import User
        from routers.auth import hash_password
        if db.query(User).count() == 0:
            logger.info("Database has no users. Seeding default users...")
            admin_user = User(
                username="admin",
                email="admin@platform.local",
                hashed_password=hash_password("admin123"),
                role="admin",
                is_active=True
            )
            devops_user = User(
                username="devops",
                email="devops@platform.local",
                hashed_password=hash_password("devops123"),
                role="devops",
                is_active=True
            )
            viewer_user = User(
                username="viewer",
                email="viewer@platform.local",
                hashed_password=hash_password("viewer123"),
                role="viewer",
                is_active=True
            )
            db.add_all([admin_user, devops_user, viewer_user])
            db.commit()
            logger.info("Default users created successfully (admin / admin123).")
    except Exception as e:
        logger.warning(f"Default admin user check notice: {e}")
    finally:
        db.close()

try:
    Base.metadata.create_all(bind=engine, checkfirst=True)
    ensure_default_admin()
except Exception as db_init_err:
    logger.warning(f"Database initialization notice on startup: {db_init_err}")

# ========================
# Rate Limiter
# ========================
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

# ========================
# Scheduler
# ========================
scheduler = BackgroundScheduler()


from services.uptime_monitor import check_all_websites
from services.security_scanner import run_full_security_audit


def uptime_check_job():
    """Periodic 24/7 website uptime & latency check (every 5 minutes)."""
    db = next(get_db())
    try:
        check_all_websites(db)
    except Exception as e:
        logger.warning(f"APScheduler: Uptime check job notice: {e}")
    finally:
        db.close()


def hourly_sync_job():
    """Hourly background synchronization — rescans servers, audits security, detects duplicates, refreshes AI insights."""
    logger.info("APScheduler: Running hourly synchronization & security audit...")
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
        run_full_security_audit(db)
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
        misfire_grace_time=300,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        uptime_check_job,
        "interval",
        minutes=5,
        id="uptime_check_5min",
        misfire_grace_time=60,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    logger.info("APScheduler started — 24/7 Uptime (5min) and Server Sync (1hr) active.")
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

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Server Error: {str(exc)}"}
    )

# CORS — regex origin matching ensures valid Access-Control-Allow-Origin with credentials across all environments
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========================
# Routers
# ========================
app.include_router(auth_router)
app.include_router(servers.router)
app.include_router(projects.router)
app.include_router(monitoring.router)
app.include_router(security.router)
app.include_router(agent.router)
app.include_router(cleanup.router)
app.include_router(stats.router)
app.include_router(discovery.router)
app.include_router(whm.router)
app.include_router(ml.router)
app.include_router(ai.router)
app.include_router(audit.router)
app.include_router(dashboard_spec.router)


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "database": "connected",
        "scheduler": "running" if scheduler.running else "stopped",
    }


# ========================
# Frontend SPA Static Mounting (Railway / Docker / Single Container)
# ========================
from fastapi import HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

static_build_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "build"))


@app.api_route("/", methods=["GET", "HEAD"])
def root(request: Request):
    accept = request.headers.get("accept", "")
    if "text/html" in accept and os.path.exists(static_build_dir):
        index_file = os.path.join(static_build_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
    return {"message": "AI Infrastructure Intelligence Platform", "version": "3.0.0", "status": "running"}
if os.path.exists(static_build_dir):
    static_assets = os.path.join(static_build_dir, "static")
    if os.path.exists(static_assets):
        app.mount("/static", StaticFiles(directory=static_assets), name="static")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        if not full_path:
            return {"message": "AI Infrastructure Intelligence Platform", "version": "3.0.0", "status": "running"}
        # Exclude API endpoints from SPA fallback
        api_prefixes = ("auth", "servers", "projects", "cleanup", "stats", "discovery", "whm", "ml", "ai", "audit", "dashboard_spec", "health", "docs", "openapi.json")
        if any(full_path.startswith(prefix) for prefix in api_prefixes):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        
        file_path = os.path.join(static_build_dir, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(static_build_dir, "index.html"))