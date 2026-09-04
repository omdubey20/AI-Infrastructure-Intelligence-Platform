"""
AI Infrastructure Intelligence Platform
Main FastAPI Backend Server
- Rate limiting (slowapi)
- Strict CORS (no wildcard in production)
- APScheduler with misfire guard
- Uptime monitoring (60s checks)
- Agent heartbeat monitoring
"""
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from apscheduler.schedulers.background import BackgroundScheduler
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from database import Base, engine, get_db
from models import Server, ProjectDiscovery, Alert
from services.server_scanner import scan_server_projects
from services.ai_insights_engine import generate_all_insights
from services.duplicate_detector import detect_duplicates
from services.uptime_monitor import uptime_check_job

from routers import stats, projects, servers, discovery, whm, ml, ai, audit, dashboard_spec
from routers import monitoring as monitoring_router
from routers import alerts as alerts_router
from routers import agent as agent_router
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

def migrate_db_schema():
    """Ensure all required columns exist in PostgreSQL and SQLite without errors."""
    from sqlalchemy import text, inspect
    
    is_sqlite = "sqlite" in str(engine.url)
    
    pg_migrations = [
        'ALTER TABLE "servers" ADD COLUMN IF NOT EXISTS "agent_api_key" VARCHAR',
        'ALTER TABLE "servers" ADD COLUMN IF NOT EXISTS "agent_installed" BOOLEAN DEFAULT FALSE',
        'ALTER TABLE "servers" ADD COLUMN IF NOT EXISTS "agent_last_seen" TIMESTAMP',
        'ALTER TABLE "alerts" ADD COLUMN IF NOT EXISTS "notification_sent" BOOLEAN DEFAULT FALSE',
        'ALTER TABLE "alerts" ADD COLUMN IF NOT EXISTS "teams_sent_at" TIMESTAMP',
        'ALTER TABLE "alerts" ADD COLUMN IF NOT EXISTS "whatsapp_sent_at" TIMESTAMP',
        'ALTER TABLE "alerts" ADD COLUMN IF NOT EXISTS "email_sent_at" TIMESTAMP',
        'ALTER TABLE "alerts" ADD COLUMN IF NOT EXISTS "site_id" INTEGER',
        'ALTER TABLE "alerts" ADD COLUMN IF NOT EXISTS "resolved_at" TIMESTAMP',
        'ALTER TABLE "alert_configs" ADD COLUMN IF NOT EXISTS "whatsapp_enabled" BOOLEAN DEFAULT TRUE',
        'ALTER TABLE "alert_configs" ADD COLUMN IF NOT EXISTS "whatsapp_user_phone" VARCHAR(50)',
        'ALTER TABLE "alert_configs" ADD COLUMN IF NOT EXISTS "whatsapp_group_id" VARCHAR(100)',
        'ALTER TABLE "alert_configs" ADD COLUMN IF NOT EXISTS "whatsapp_provider" VARCHAR(50) DEFAULT \'callmebot\'',
        'ALTER TABLE "alert_configs" ADD COLUMN IF NOT EXISTS "whatsapp_api_key" VARCHAR(255)',
        'ALTER TABLE "alert_configs" ADD COLUMN IF NOT EXISTS "whatsapp_gateway_url" VARCHAR(500)',
        'ALTER TABLE "alert_configs" ADD COLUMN IF NOT EXISTS "whatsapp_account_sid" VARCHAR(100)',
        'ALTER TABLE "alert_configs" ADD COLUMN IF NOT EXISTS "whatsapp_from_phone" VARCHAR(50)',
        'ALTER TABLE "alert_configs" ADD COLUMN IF NOT EXISTS "email_to" VARCHAR(255)',
        'ALTER TABLE "alert_configs" ADD COLUMN IF NOT EXISTS "smtp_host" VARCHAR(255)',
        'ALTER TABLE "alert_configs" ADD COLUMN IF NOT EXISTS "smtp_port" INTEGER DEFAULT 587',
        'ALTER TABLE "alert_configs" ADD COLUMN IF NOT EXISTS "smtp_user" VARCHAR(255)',
        'ALTER TABLE "alert_configs" ADD COLUMN IF NOT EXISTS "smtp_password" VARCHAR(255)',
    ]

    if is_sqlite:
        with engine.begin() as conn:
            inspector = inspect(conn)
            tables = inspector.get_table_names()
            sqlite_columns = {
                "servers": [
                    ("agent_api_key", "VARCHAR"),
                    ("agent_installed", "BOOLEAN DEFAULT 0"),
                    ("agent_last_seen", "TIMESTAMP"),
                ],
                "alerts": [
                    ("notification_sent", "BOOLEAN DEFAULT 0"),
                    ("teams_sent_at", "TIMESTAMP"),
                    ("whatsapp_sent_at", "TIMESTAMP"),
                    ("email_sent_at", "TIMESTAMP"),
                    ("site_id", "INTEGER"),
                    ("resolved_at", "TIMESTAMP"),
                ],
                "alert_configs": [
                    ("whatsapp_enabled", "BOOLEAN DEFAULT 1"),
                    ("whatsapp_user_phone", "VARCHAR(50)"),
                    ("whatsapp_group_id", "VARCHAR(100)"),
                    ("whatsapp_provider", "VARCHAR(50) DEFAULT 'callmebot'"),
                    ("whatsapp_api_key", "VARCHAR(255)"),
                    ("whatsapp_gateway_url", "VARCHAR(500)"),
                    ("whatsapp_account_sid", "VARCHAR(100)"),
                    ("whatsapp_from_phone", "VARCHAR(50)"),
                    ("email_to", "VARCHAR(255)"),
                    ("smtp_host", "VARCHAR(255)"),
                    ("smtp_port", "INTEGER DEFAULT 587"),
                    ("smtp_user", "VARCHAR(255)"),
                    ("smtp_password", "VARCHAR(255)"),
                ],
            }
            for table, cols in sqlite_columns.items():
                if table in tables:
                    existing = [col["name"] for col in inspector.get_columns(table)]
                    for col_name, col_type in cols:
                        if col_name not in existing:
                            try:
                                conn.execute(text(f'ALTER TABLE "{table}" ADD COLUMN "{col_name}" {col_type}'))
                            except Exception as ex:
                                logger.debug(f"SQLite migration notice ({table}.{col_name}): {ex}")
    else:
        for sql in pg_migrations:
            try:
                with engine.begin() as conn:
                    conn.execute(text(sql))
            except Exception as e:
                logger.debug(f"PostgreSQL migration skipped: {e}")
    logger.info("migrate_db_schema: complete")


# ========================
# Rate Limiter
# ========================
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

# ========================
# Scheduler & Lifespan
# ========================
scheduler = BackgroundScheduler()


def fleet_background_sync_job():
    """Background fleet synchronization (every 10 min) — rescans server metrics, detects duplicates, refreshes AI insights & retrains ML pipeline."""
    logger.info("APScheduler: Running 10-minute fleet background sync job...")
    db = next(get_db())
    try:
        all_servers = db.query(Server).all()
        for server in all_servers:
            if server.agent_installed and server.data_source == "agent":
                continue
            try:
                scan_server_projects(db, server, triggered_by="scheduler")
            except Exception as scan_err:
                logger.warning(f"APScheduler: Failed to scan {server.name}: {scan_err}")

        discoveries = db.query(ProjectDiscovery).all()
        detect_duplicates(discoveries)
        generate_all_insights(db)

        # Background automated ML model retraining with latest fleet telemetry
        try:
            from services.ml_pipeline import train_and_evaluate_pipeline
            train_and_evaluate_pipeline(db=db)
            logger.info("APScheduler: Automated ML pipeline retraining completed.")
        except Exception as ml_sync_err:
            logger.warning(f"APScheduler ML retraining notice: {ml_sync_err}")

        db.commit()
    except Exception as e:
        logger.error(f"APScheduler sync job error: {e}")
        db.rollback()
    finally:
        db.close()
    logger.info("APScheduler: Fleet background sync job completed.")


def agent_heartbeat_check():
    """Check if agents are still reporting. Flag servers as unreachable if no heartbeat in 3 minutes."""
    db = next(get_db())
    try:
        cutoff = datetime.utcnow() - timedelta(minutes=3)
        stale_servers = db.query(Server).filter(
            Server.agent_installed == True,
            Server.agent_last_seen < cutoff,
            Server.status != "agent_offline",
        ).all()

        for server in stale_servers:
            server.status = "agent_offline"
            existing = db.query(Alert).filter(
                Alert.server_id == server.id,
                Alert.type == "agent_offline",
                Alert.is_resolved == False,
            ).first()
            if not existing:
                from services.notification_service import create_and_dispatch_alert
                create_and_dispatch_alert(
                    db,
                    alert_type="agent_offline",
                    severity="critical",
                    message=f"Agent on {server.name} ({server.ip_address}) has stopped reporting. Last seen: {server.agent_last_seen}",
                    server_id=server.id,
                    server_name=server.name,
                )

        online_servers = db.query(Server).filter(
            Server.agent_installed == True,
            Server.agent_last_seen >= cutoff,
        ).all()
        for server in online_servers:
            if server.status == "agent_offline":
                server.status = "active"
            open_alerts = db.query(Alert).filter(
                Alert.server_id == server.id,
                Alert.type == "agent_offline",
                Alert.is_resolved == False,
            ).all()
            for a in open_alerts:
                a.is_resolved = True
                a.resolved_at = datetime.utcnow()

        db.commit()
    except Exception as e:
        logger.error(f"Agent heartbeat check error: {e}")
        db.rollback()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run DB init and server auto-scans in a background thread so lifespan yields IMMEDIATELY
    import threading

    def _background_db_init():
        try:
            Base.metadata.create_all(bind=engine, checkfirst=True)
            migrate_db_schema()
            ensure_default_admin()
            logger.info("Database background initialization completed successfully.")

            # Auto-train ML model on startup if missing so Model Status is immediately ACTIVE
            from services.ml_pipeline import MODEL_PATH, train_and_evaluate_pipeline
            if not os.path.exists(MODEL_PATH):
                logger.info("Startup ML Auto-Trainer: Training initial ML model...")
                db = next(get_db())
                try:
                    train_and_evaluate_pipeline(db=db)
                    logger.info("Startup ML Auto-Trainer: ML model training completed successfully.")
                except Exception as ml_init_err:
                    logger.warning(f"Startup ML auto-training notice: {ml_init_err}")
                finally:
                    db.close()

            # Auto-scan all servers on startup so fresh live data is fetched immediately
            db_scan = next(get_db())
            try:
                all_srvs = db_scan.query(Server).all()
                for s in all_srvs:
                    logger.info(f"Startup Scanner: Auto-scanning server {s.name} ({s.ip_address})...")
                    scan_server_projects(db_scan, s)
            except Exception as scan_init_err:
                logger.warning(f"Startup auto-scan notice: {scan_init_err}")
            finally:
                db_scan.close()

            # Run immediate uptime health checks on startup
            from services.uptime_monitor import run_uptime_checks
            db_uptime = next(get_db())
            try:
                logger.info("Startup Uptime Monitor: Running initial website health checks...")
                run_uptime_checks(db_uptime)
                logger.info("Startup Uptime Monitor: Health checks completed.")
            except Exception as uptime_init_err:
                logger.warning(f"Startup uptime check notice: {uptime_init_err}")
            finally:
                db_uptime.close()
        except Exception as db_init_err:
            logger.warning(f"Database initialization notice: {db_init_err}")

    threading.Thread(target=_background_db_init, daemon=True).start()

    scheduler.add_job(
        fleet_background_sync_job,
        "interval",
        minutes=10,
        id="fleet_sync",
        misfire_grace_time=120,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        uptime_check_job,
        "interval",
        minutes=5,
        id="uptime_checks",
        misfire_grace_time=120,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        agent_heartbeat_check,
        "interval",
        minutes=5,
        id="agent_heartbeat",
        misfire_grace_time=60,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    logger.info("APScheduler started — hourly sync, 60s uptime checks, 5min agent heartbeat active.")
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
app.include_router(stats.router)
app.include_router(discovery.router)
app.include_router(whm.router)
app.include_router(ml.router)
app.include_router(ai.router)
app.include_router(audit.router)
app.include_router(dashboard_spec.router)
app.include_router(monitoring_router.router)
app.include_router(alerts_router.router)
app.include_router(agent_router.router)


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
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

static_build_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "build"))


@app.api_route("/", methods=["GET", "HEAD"])
def root(request: Request):
    accept = request.headers.get("accept", "")
    if "text/html" in accept and static_build_dir and os.path.exists(static_build_dir):
        index_file = os.path.join(static_build_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
    return {"message": "AI Infrastructure Intelligence Platform", "version": "3.0.0", "status": "running"}


if os.path.exists(static_build_dir):
    static_assets = os.path.join(static_build_dir, "static")
    if os.path.exists(static_assets):
        app.mount("/static", StaticFiles(directory=static_assets), name="static")

    @app.get("/{full_path:path}")
    def serve_spa(request: Request, full_path: str):
        # 1. If static file exists directly (e.g. favicon.ico, manifest.json)
        file_path = os.path.join(static_build_dir, full_path)
        if full_path and os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        
        # 2. For all client-side routes (/monitoring, /servers, /alerts, /projects, etc.) -> index.html
        index_file = os.path.join(static_build_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)

        return {"message": "AI Infrastructure Intelligence Platform", "version": "3.0.0", "status": "running"}