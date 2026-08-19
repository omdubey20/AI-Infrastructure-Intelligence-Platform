"""
Discovery Router — Parallel server scan trigger.
Requires devops or admin role to trigger scans.
"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db, SessionLocal
from models import Server, ProjectDiscovery
from routers.auth import get_current_user, require_role
from services.server_scanner import scan_server_projects
from services.duplicate_detector import detect_duplicates
from services.inactive_detector import detect_inactive_projects
from services.ai_insights_engine import generate_all_insights

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/discovery", tags=["Discovery"])


def _scan_one(server_id: int):
    """Run a scan for a single server in its own DB session."""
    db = SessionLocal()
    try:
        server = db.query(Server).filter(Server.id == server_id).first()
        if not server:
            return {"server_id": server_id, "status": "not_found"}
        result = scan_server_projects(db, server)
        return {"server_id": server_id, "server_name": server.name, **result}
    except Exception as e:
        logger.error(f"Scan error for server {server_id}: {e}")
        db.rollback()
        return {"server_id": server_id, "status": "error", "error": str(e)}
    finally:
        db.close()


@router.post("/scan")
def trigger_scan(
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin", "devops"]))
):
    """Trigger a parallel SSH / WHM scan across all registered servers (100% real live discovery)."""
    servers = db.query(Server).all()
    if not servers:
        return {"message": "No servers registered to scan", "servers_scanned": 0}

    server_ids = [s.id for s in servers]
    results = []

    with ThreadPoolExecutor(max_workers=min(4, len(server_ids))) as executor:
        futures = {executor.submit(_scan_one, sid): sid for sid in server_ids}
        for future in as_completed(futures):
            try:
                results.append(future.result(timeout=60))
            except Exception as e:
                results.append({"server_id": futures[future], "error": str(e)})

    # Refresh post-scan intelligence
    try:
        all_disc = db.query(ProjectDiscovery).all()
        detect_duplicates(all_disc)
        detect_inactive_projects(all_disc)
        generate_all_insights(db)
        db.commit()
    except Exception as e:
        logger.error(f"Post-scan intelligence error: {e}")
        db.rollback()

    total_projects = db.query(ProjectDiscovery).count()
    return {
        "message": "Infrastructure discovery completed",
        "servers_scanned": len(results),
        "total_projects_discovered": total_projects,
        "scan_results": results,
        "completed_at": datetime.utcnow().isoformat(),
    }


@router.post("/scan/{server_id}")
def trigger_scan_single(
    server_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin", "devops"]))
):
    """Trigger discovery scan on a single server."""
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    result = scan_server_projects(db, server)

    try:
        all_disc = db.query(ProjectDiscovery).all()
        detect_duplicates(all_disc)
        detect_inactive_projects(all_disc)
        db.commit()
    except Exception as e:
        logger.warning(f"Post-scan intelligence error: {e}")
        db.rollback()

    return {
        "message": f"Scan completed for {server.name}",
        "server_id": server_id,
        **result,
    }


@router.get("/status")
def scan_status(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Get current scan status for all servers."""
    servers = db.query(Server).all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "ip_address": s.ip_address,
            "scan_status": getattr(s, "scan_status", "never_scanned"),
            "last_scanned_at": s.last_scanned_at.isoformat() if s.last_scanned_at else None,
            "data_source": s.data_source or "estimated",
            "projects_count": db.query(ProjectDiscovery).filter(
                ProjectDiscovery.server_id == s.id
            ).count(),
        }
        for s in servers
    ]
