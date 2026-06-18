from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from database import Base, engine, get_db
from models import Server
from services.server_scanner import scan_server_projects
from routers import stats, projects, servers, cleanup, discovery
from routers.auth import router as auth_router
import models
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine, checkfirst=True)

scheduler = BackgroundScheduler()


def nightly_scan_job():
    logger.info("APScheduler: Starting nightly scan...")
    db = next(get_db())
    try:
        all_servers = db.query(Server).all()
        for server in all_servers:
            try:
                scan_server_projects(db, server)
                logger.info(f"APScheduler: Scanned {server.name}")
            except Exception as e:
                logger.error(f"APScheduler: Failed to scan {server.name}: {e}")
    finally:
        db.close()
    logger.info("APScheduler: Nightly scan complete.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(nightly_scan_job, "cron", hour=2, minute=0, id="nightly_scan")
    scheduler.start()
    logger.info("APScheduler started — nightly scan scheduled at 2:00 AM")
    yield
    scheduler.shutdown()
    logger.info("APScheduler stopped")


app = FastAPI(
    title="AI Infrastructure Intelligence Platform",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "https://ai-infrastructure-intelligence-plat.vercel.app",
        "https://ai-infrastructure-intelligence-plat-eta.vercel.app",
    ],
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


@app.api_route("/", methods=["GET", "HEAD"])
def root():
    return {"message": "AI Infrastructure Intelligence Platform", "status": "running"}


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "database": "connected",
        "scheduler": "running" if scheduler.running else "stopped"
    }