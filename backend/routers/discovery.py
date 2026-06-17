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
    finally:
        db.close()

@router.post("/scan")
def trigger_scan(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    stats_module._cache = {"data": None, "ts": 0}  # clear dashboard cache
    background_tasks.add_task(run_scan_job)
    return {"message": "Scan started in background"}

@router.get("/results")
def get_results(db: Session = Depends(get_db)):
    servers = db.query(Server).all()
    return [{"id": s.id, "hostname": s.hostname, "ip_address": s.ip_address, "status": s.status} for s in servers]
