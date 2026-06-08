from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from routers.auth import get_current_user
import models, schemas
from typing import List
from datetime import datetime, timedelta

router = APIRouter(prefix="/cleanup", tags=["Cleanup"])


@router.get("/report")
def get_cleanup_report(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    three_years_ago = datetime.utcnow() - timedelta(days=1095)
    one_year_ago = datetime.utcnow() - timedelta(days=365)

    all_projects = db.query(models.Project).all()

    # Find duplicates
    name_count = {}
    for p in all_projects:
        name_count[p.name] = name_count.get(p.name, 0) + 1

    report = []
    for project in all_projects:
        server = db.query(models.Server).filter(models.Server.id == project.server_id).first()
        action = "keep"

        if project.last_modified and project.last_modified < three_years_ago:
            if not project.dns_points_here and not project.web_config_active:
                action = "delete"
        elif project.last_modified and project.last_modified < one_year_ago:
            if not project.dns_points_here:
                action = "archive"
        elif name_count.get(project.name, 0) > 1 and not project.dns_points_here:
            action = "remove_duplicate"

        report.append({
            "project_id": project.id,
            "project_name": project.name,
            "server_name": server.name if server else "Unknown",
            "server_id": project.server_id,
            "status": project.status,
            "last_modified": project.last_modified,
            "dns_active": project.dns_points_here,
            "web_config_active": project.web_config_active,
            "size_mb": project.size_mb,
            "is_duplicate": name_count.get(project.name, 0) > 1,
            "recommended_action": action
        })

    return {
        "total_projects": len(all_projects),
        "delete_candidates": len([r for r in report if r["recommended_action"] == "delete"]),
        "archive_candidates": len([r for r in report if r["recommended_action"] == "archive"]),
        "duplicate_candidates": len([r for r in report if r["recommended_action"] == "remove_duplicate"]),
        "keep_count": len([r for r in report if r["recommended_action"] == "keep"]),
        "projects": report
    }


@router.post("/approve/{project_id}")
def approve_cleanup_action(
    project_id: int,
    action: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    server = db.query(models.Server).filter(models.Server.id == project.server_id).first()

    if action == "delete":
        log = models.CleanupLog(
            project_name=project.name,
            server_name=server.name if server else "Unknown",
            action="deleted",
            performed_by=current_user.username,
            notes="Deleted via cleanup approval"
        )
        db.add(log)
        db.delete(project)
        db.commit()
        return {"message": f"Project '{project.name}' deleted successfully"}

    elif action == "archive":
        project.status = "archive"
        log = models.CleanupLog(
            project_name=project.name,
            server_name=server.name if server else "Unknown",
            action="archived",
            performed_by=current_user.username,
            notes="Archived via cleanup approval"
        )
        db.add(log)
        db.commit()
        return {"message": f"Project '{project.name}' archived successfully"}

    elif action == "keep":
        project.status = "live"
        db.commit()
        return {"message": f"Project '{project.name}' marked as keep"}

    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use: delete, archive, keep")


@router.get("/logs", response_model=List[schemas.CleanupLogOut])
def get_cleanup_logs(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return db.query(models.CleanupLog).order_by(models.CleanupLog.performed_at.desc()).all()


@router.get("/stats")
def get_stats(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    total_servers = db.query(models.Server).count()
    total_projects = db.query(models.Project).count()
    live_projects = db.query(models.Project).filter(models.Project.status == "live").count()
    unused_projects = db.query(models.Project).filter(models.Project.status == "unused").count()
    online_servers = db.query(models.Server).filter(models.Server.status == "online").count()

    return {
        "total_servers": total_servers,
        "total_projects": total_projects,
        "live_projects": live_projects,
        "unused_projects": unused_projects,
        "online_servers": online_servers,
        "offline_servers": total_servers - online_servers
    }