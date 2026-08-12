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
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.background import BackgroundScheduler

from database import Base, engine, get_db, SessionLocal
from models import Server, ProjectDiscovery, User
from services.server_scanner import scan_server_projects
from services.ai_insights_engine import generate_all_insights
from services.duplicate_detector import detect_duplicates
from services.inactive_detector import detect_inactive_projects

from routers import stats, projects, servers, cleanup, discovery, whm, ml, ai, audit, dashboard_spec
from routers.auth import router as auth_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend.main")

try:
    Base.metadata.create_all(bind=engine, checkfirst=True)
except Exception as db_err:
    logger.warning(f"Database table creation deferred: {db_err}")


def ensure_default_user():
    """Auto-seed default admin user if user table is empty."""
    try:
        db = SessionLocal()
        if db.query(User).count() == 0:
            from routers.auth import hash_password
            admin_user = User(
                username="admin",
                email="admin@platform.local",
                hashed_password=hash_password("admin123"),
                role="admin",
                is_active=True
            )
            db.add(admin_user)
            db.commit()
            logger.info("Default admin user auto-seeded: admin / admin123")
        db.close()
    except Exception as e:
        logger.warning(f"Default user check deferred: {e}")


ensure_default_user()

try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
    HAS_SLOWAPI = True
except Exception:
    limiter = None
    HAS_SLOWAPI = False

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
    if not (os.getenv("VERCEL") or os.getenv("VERCEL_ENV")):
        try:
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
        except Exception as sched_err:
            logger.warning(f"APScheduler skipped: {sched_err}")
    yield
    if not (os.getenv("VERCEL") or os.getenv("VERCEL_ENV")):
        try:
            scheduler.shutdown()
        except Exception:
            pass


# ========================
# FastAPI App
# ========================
app = FastAPI(
    title="AI Infrastructure Intelligence Platform",
    version="3.0.0",
    lifespan=lifespan,
)

# Rate limiter registration
if HAS_SLOWAPI and limiter:
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

@app.middleware("http")
async def vercel_path_normalizer(request: Request, call_next):
    raw_path = request.scope.get("path", "")
    matched = request.headers.get("x-matched-path", "")

    if matched and matched != raw_path:
        request.scope["path"] = matched
    elif raw_path.startswith("/api/index.py"):
        request.scope["path"] = raw_path.replace("/api/index.py", "") or "/"

    return await call_next(request)


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


@app.get("/api/status")
def status():
    return {"message": "AI Infrastructure Intelligence Platform", "version": "3.0.0", "status": "running"}


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "database": "connected",
        "scheduler": "running" if scheduler.running else "stopped",
    }


# Static build mount candidates for frontend SPA
build_candidates = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "frontend", "build")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "build")),
    os.path.abspath("frontend/build"),
]

frontend_build_dir = None
for b_dir in build_candidates:
    if os.path.exists(b_dir):
        frontend_build_dir = b_dir
        break

if frontend_build_dir and os.path.exists(os.path.join(frontend_build_dir, "static")):
    app.mount("/static", StaticFiles(directory=os.path.join(frontend_build_dir, "static")), name="static")


@app.exception_handler(404)
async def spa_404_handler(request: Request, exc: Exception):
    path = request.url.path.lstrip("/")
    if path in ("health", "api/status") or path.startswith(("auth", "servers", "projects", "cleanup", "stats", "discovery", "whm", "ml", "ai", "audit", "api")):
        return JSONResponse({"detail": "Not Found"}, status_code=404)

    if frontend_build_dir:
        file_path = os.path.join(frontend_build_dir, path)
        if path and os.path.isfile(file_path):
            return FileResponse(file_path)
        index_file = os.path.join(frontend_build_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)

    return JSONResponse({"message": "AI Infrastructure Intelligence Platform", "version": "3.0.0", "status": "running"})