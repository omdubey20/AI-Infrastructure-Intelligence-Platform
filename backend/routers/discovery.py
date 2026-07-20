from fastapi import APIRouter, Depends, BackgroundTasks
from routers import stats as stats_module
from sqlalchemy.orm import Session
from database import get_db, SessionLocal
from models import Server
from services.server_scanner import scan_server_projects

router = APIRouter(prefix="/discovery", tags=["Discovery"])


def run_scan_job():
    db = SessionLocal()
    try:
        servers = db.query(Server).all()
        for server in servers:
            scan_server_projects(db, server)
        stats_module._cache = {"data": None, "ts": 0}
    finally:
        db.close()


@router.post("/scan")
def trigger_scan(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    servers = db.query(Server).all()
    server_count = len(servers)

    stats_module._cache = {"data": None, "ts": 0}
    background_tasks.add_task(run_scan_job)

    return {
        "message": f"Scan started for {server_count} server(s)",
        "scanned_servers": server_count
    }


@router.get("/results")
def get_results(db: Session = Depends(get_db)):
    servers = db.query(Server).all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "ip_address": s.ip_address,
            "status": s.status
        }
        for s in servers
    ]