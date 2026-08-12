"""
Cleanup Router
Provides approval-based cleanup recommendations and audit history.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import models
from database import get_db
from routers.auth import get_current_user, require_role
from routers.audit import create_audit_entry

router = APIRouter(prefix="/cleanup", tags=["Cleanup"])


@router.get("/report")
def cleanup_report(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    discoveries = db.query(models.ProjectDiscovery).all()

    projects = []
    delete_count = archive_count = keep_count = 0

    for item in discoveries:
        rec = getattr(item, "recommendation", "keep") or "keep"
        rec_upper = rec.upper()

        if item.is_inactive and rec_upper != "KEEP":
            rec_upper = "DELETE" if (item.days_since_modified or 0) > 1460 else "ARCHIVE"
        elif item.is_duplicate and rec_upper != "KEEP":
            rec_upper = "DELETE"

        if rec_upper == "DELETE":
            delete_count += 1
        elif rec_upper == "ARCHIVE":
            archive_count += 1
        else:
            keep_count += 1

        reason = "Active project"
        if item.is_duplicate:
            reason = "Duplicate copy detected"
        elif item.is_inactive:
            reason = f"Unused for {item.days_since_modified or 1120} days (>3 years)"

        projects.append({
            "projectid": item.id,
            "projectname": item.project_name,
            "servername": item.server.name if item.server else "Unknown",
            "domain": item.domain,
            "riskscore": item.risk_score or 0,
            "recommendedaction": rec_upper,
            "duplicateconfidence": item.duplicate_confidence or 0,
            "is_duplicate": item.is_duplicate,
            "is_inactive": item.is_inactive,
            "days_since_modified": item.days_since_modified or 0,
            "reason": reason,
            "dns_points_here": item.dns_points_here,
            "web_config_active": item.web_config_active,
            "created_at": item.created_at.isoformat() if item.created_at else None
        })

    return {
        "totalprojects": len(discoveries),
        "deletecandidates": delete_count,
        "archivecandidates": archive_count,
        "keepcount": keep_count,
        "projects": projects
    }


@router.post("/approve/{project_id}")
def approve_cleanup(project_id: int, action: str, db: Session = Depends(get_db), current_user=Depends(require_role(["admin", "devops"]))):
    project = db.query(models.ProjectDiscovery).filter(models.ProjectDiscovery.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    name = project.project_name
    server_name = project.server.name if project.server else "Unknown"

    if action == "delete":
        # Clear duplicate_of_id references
        db.query(models.ProjectDiscovery).filter(models.ProjectDiscovery.duplicate_of_id == project_id).update({models.ProjectDiscovery.duplicate_of_id: None}, synchronize_session=False)

        # Delete AI Insights referencing this project
        db.query(models.AIInsight).filter(models.AIInsight.project_id == project_id).delete(synchronize_session=False)

        db.delete(project)
        db.commit()
        message = f"Project '{name}' deleted successfully"
    elif action == "archive":
        project.env_type = "archived"
        project.recommendation = "archive"
        project.user_override = "archive"
        project.is_duplicate = False
        project.is_inactive = False
        db.commit()
        message = f"Project '{name}' marked as archived"
    elif action == "keep":
        project.is_duplicate = False
        project.is_inactive = False
        project.recommendation = "keep"
        project.user_override = "keep"
        project.env_type = "live"
        db.commit()
        message = f"Project '{name}' marked as keep"
    else:
        raise HTTPException(status_code=400, detail="Invalid action")

    create_audit_entry(
        db,
        action=f"cleanup_{action}",
        entity_type="project",
        entity_id=project_id,
        entity_name=name,
        details=f"Performed action '{action}' on server '{server_name}'",
        user_id=current_user.id if current_user else None
    )

    return {"success": True, "project_id": project_id, "action": action, "message": message}


@router.get("/logs")
def get_cleanup_logs(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    logs = (
        db.query(models.AuditLog)
        .filter(models.AuditLog.action.like("cleanup_%"))
        .order_by(models.AuditLog.created_at.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "id": l.id,
            "projectname": l.entity_name,
            "action": l.action.replace("cleanup_", ""),
            "details": l.details,
            "performedby": l.user.username if l.user else "System",
            "created_at": l.created_at.isoformat() if l.created_at else None
        }
        for l in logs
    ]
