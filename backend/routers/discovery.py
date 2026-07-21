from fastapi import APIRouter, Depends
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
def trigger_scan(db: Session = Depends(get_db)):
    try:
        from routers import stats as stats_module
        stats_module._cache = {"data": None, "ts": 0}
    except Exception:
        pass
    try:
        run_scan_job()
        count = db.query(Server).count()
        return {"message": "Scan completed", "servers_scanned": count}
    except Exception as e:
        return {"message": f"Scan failed: {str(e)}"}

@router.get("/results")
def get_results(db: Session = Depends(get_db)):
    servers = db.query(Server).all()
    return [{"id": s.id, "ip_address": s.ip_address, "status": s.status} for s in servers]
