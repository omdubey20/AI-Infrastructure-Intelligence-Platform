"""
AI Infrastructure Intelligence Platform
Main FastAPI Backend Server
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler

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

scheduler = BackgroundScheduler()


def hourly_sync_job():
    """Hourly background synchronization job for metrics, discovery, AI & ML."""
    logger.info("APScheduler: Running hourly synchronization job...")
    db = next(get_db())
    try:
        discoveries = db.query(ProjectDiscovery).all()
        detect_duplicates(discoveries)
        detect_inactive_projects(discoveries)
        generate_all_insights(db)
        db.commit()
    except Exception as e:
        logger.error(f"APScheduler sync job error: {e}")
    finally:
        db.close()
    logger.info("APScheduler: Hourly sync job completed.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(hourly_sync_job, "interval", hours=1, id="hourly_sync")
    scheduler.start()
    logger.info("APScheduler started — hourly background sync active.")
    yield
    scheduler.shutdown()
    logger.info("APScheduler stopped.")


app = FastAPI(
    title="AI Infrastructure Intelligence Platform",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    return {"message": "AI Infrastructure Intelligence Platform", "version": "2.0.0", "status": "running"}


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "database": "connected",
        "scheduler": "running" if scheduler.running else "stopped"
    }]

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
    clean_path = path[4:] if path.startswith("api/") else path

    if clean_path in ("health", "status") or clean_path.startswith(("auth", "servers", "projects", "cleanup", "stats", "discovery", "whm", "ml", "ai", "audit")):
        return JSONResponse({"detail": "Not Found"}, status_code=404)

    if frontend_build_dir:
        file_path = os.path.join(frontend_build_dir, path)
        if path and os.path.isfile(file_path):
            return FileResponse(file_path)
        index_file = os.path.join(frontend_build_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)

    return JSONResponse({"message": "AI Infrastructure Intelligence Platform", "version": "3.0.0", "status": "running"})