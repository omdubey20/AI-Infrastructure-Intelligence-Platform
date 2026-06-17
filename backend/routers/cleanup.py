from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import models, time
from database import get_db
from routers.auth import get_current_user
from services.duplicate_engine import analyze_duplicates

_cleanup_cache = {"data": None, "ts": 0}
CACHE_TTL = 300

router = APIRouter(prefix="/cleanup", tags=["Cleanup"])

@router.get("/report")
def cleanup_report(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    global _cleanup_cache
    now = time.time()
    if _cleanup_cache["data"] and (now - _cleanup_cache["ts"]) < CACHE_TTL:
        return _cleanup_cache["data"]
    discoveries = db.query(models.ProjectDiscovery).all()
    duplicate_analysis = analyze_duplicates(discoveries)
    analysis_map = {item["id"]: item for item in duplicate_analysis}

    projects = []
    delete_count = archive_count = keep_count = 0

    for item in discoveries:
        analysis = analysis_map.get(item.id, {"recommendation": "KEEP", "duplicate_confidence": 0, "reason": "No analysis"})
        rec = analysis["recommendation"]

        if rec == "DELETE":
            delete_count += 1
        elif rec == "ARCHIVE":
            archive_count += 1
        else:
            keep_count += 1

        projects.append({
            "projectid": item.id,
            "projectname": item.project_name,
            "servername": item.server.name if item.server else "Unknown",
            "riskscore": item.risk_score,
            "recommendedaction": rec,
            "duplicateconfidence": analysis["duplicate_confidence"],
            "reason": analysis["reason"],
            "dns_points_here": item.dns_points_here,
            "web_config_active": item.web_config_active,
            "created_at": item.created_at.isoformat()
        })

    result = {
        "totalprojects": len(discoveries),
        "deletecandidates": delete_count,
        "archivecandidates": archive_count,
        "keepcount": keep_count,
        "projects": projects
    }
    _cleanup_cache = {"data": result, "ts": now}
    return result

@router.post("/approve/{project_id}")
def approve_cleanup(project_id: int, action: str, db: Session = Depends(get_db)):
    project = db.query(models.ProjectDiscovery).filter(models.ProjectDiscovery.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if action == "delete":
        db.delete(project)
        message = "Project deleted successfully"
    elif action == "archive":
        # You can add an archived flag later
        message = "Project archived (move logic can be added)"
    elif action == "keep":
        message = "Project marked as keep"
    else:
        raise HTTPException(status_code=400, detail="Invalid action")

    db.commit()
    return {"success": True, "project_id": project_id, "action": action, "message": message}