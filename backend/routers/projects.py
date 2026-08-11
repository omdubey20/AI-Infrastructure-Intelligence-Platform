"""
Projects Router
Supports pagination, search, filters (all, live, duplicate, inactive), server filtering, framework tags, and project detail endpoints.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
import models
from database import get_db
from routers.auth import get_current_user, require_role
from services.duplicate_detector import detect_duplicates
from services.inactive_detector import detect_inactive_projects

router = APIRouter(prefix="/projects", tags=["Projects"])


def serialize_project(p: models.ProjectDiscovery):
    server_name = p.server.name if getattr(p, "server", None) else None
    return {
        "id": p.id,
        "name": p.project_name,
        "project_name": p.project_name,
        "server_id": p.server_id,
        "server_name": server_name,
        "domain": p.domain,
        "project_path": p.project_path,
        "framework": p.framework or "unknown",
        "language": p.language or "unknown",
        "owner": p.owner,
        "size_mb": p.size_mb or 0,
        "dns_points_here": p.dns_points_here,
        "web_config_active": p.web_config_active,
        "has_ssl": getattr(p, "has_ssl", False),
        "ssl_expiry_days": getattr(p, "ssl_expiry_days", None),
        "is_live": getattr(p, "is_live", False),
        "is_duplicate": getattr(p, "is_duplicate", False),
        "is_inactive": getattr(p, "is_inactive", False),
        "days_since_modified": getattr(p, "days_since_modified", 0),
        "env_type": getattr(p, "env_type", "unknown"),
        "git_remote": getattr(p, "git_remote", None),
        "git_branch": getattr(p, "git_branch", None),
        "database_used": getattr(p, "database_used", None),
        "web_server": getattr(p, "web_server", None),
        "risk_score": p.risk_score or 0,
        "recommendation": getattr(p, "recommendation", "keep"),
        "data_source": p.data_source or "estimated",
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "last_modified": p.last_modified.isoformat() if getattr(p, "last_modified", None) else None
    }


@router.get("/")
def get_projects(
    filter_type: Optional[str] = Query("all", alias="filter"),
    search: Optional[str] = None,
    server_id: Optional[int] = None,
    framework: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(1000, ge=1, le=5000),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    query = db.query(models.ProjectDiscovery).options(joinedload(models.ProjectDiscovery.server))

    if filter_type == "suspended":
        query = query.filter(models.ProjectDiscovery.is_inactive == True)
    elif filter_type == "duplicates":
        query = query.filter(models.ProjectDiscovery.is_duplicate == True)
    elif filter_type == "inactive":
        query = query.filter(models.ProjectDiscovery.is_inactive == True)
    elif filter_type == "live":
        query = query.filter(models.ProjectDiscovery.is_live == True, models.ProjectDiscovery.is_inactive == False)


    if server_id:
        query = query.filter(models.ProjectDiscovery.server_id == server_id)

    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            models.ProjectDiscovery.project_name.ilike(s) |
            models.ProjectDiscovery.domain.ilike(s) |
            models.ProjectDiscovery.project_path.ilike(s)
        )

    if framework:
        query = query.filter(models.ProjectDiscovery.framework.ilike(f"%{framework}%"))

    total = query.count()
    projects = query.order_by(models.ProjectDiscovery.id.desc()).offset((page - 1) * limit).limit(limit).all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "projects": [serialize_project(p) for p in projects]
    }


@router.get("/duplicates")
def get_duplicate_projects(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    duplicates = db.query(models.ProjectDiscovery).filter(
        models.ProjectDiscovery.is_duplicate == True
    ).options(joinedload(models.ProjectDiscovery.server)).all()

    if not duplicates:
        discoveries = db.query(models.ProjectDiscovery).options(joinedload(models.ProjectDiscovery.server)).all()
        detect_duplicates(discoveries)
        db.commit()
        duplicates = [p for p in discoveries if p.is_duplicate]

    return [serialize_project(p) for p in duplicates]


@router.get("/inactive")
def get_inactive_projects(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    inactives = db.query(models.ProjectDiscovery).filter(
        models.ProjectDiscovery.is_inactive == True
    ).options(joinedload(models.ProjectDiscovery.server)).all()

    if not inactives:
        discoveries = db.query(models.ProjectDiscovery).options(joinedload(models.ProjectDiscovery.server)).all()
        detect_inactive_projects(discoveries)
        db.commit()
        inactives = [p for p in discoveries if p.is_inactive]

    return [serialize_project(p) for p in inactives]


@router.get("/server/{server_id}")
def get_projects_by_server(
    server_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    projects = db.query(models.ProjectDiscovery).filter(
        models.ProjectDiscovery.server_id == server_id
    ).options(joinedload(models.ProjectDiscovery.server)).all()
    return [serialize_project(p) for p in projects]


@router.get("/{project_id}")
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    project = db.query(models.ProjectDiscovery).filter(
        models.ProjectDiscovery.id == project_id
    ).options(joinedload(models.ProjectDiscovery.server)).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return serialize_project(project)


@router.delete("/{project_id}")
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin", "devops"]))
):
    project = db.query(models.ProjectDiscovery).filter(
        models.ProjectDiscovery.id == project_id
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    name = project.project_name

    # Clear duplicate_of_id references
    db.query(models.ProjectDiscovery).filter(models.ProjectDiscovery.duplicate_of_id == project_id).update({models.ProjectDiscovery.duplicate_of_id: None}, synchronize_session=False)

    # Delete AI Insights referencing this project
    db.query(models.AIInsight).filter(models.AIInsight.project_id == project_id).delete(synchronize_session=False)

    db.delete(project)
    db.commit()

    return {"message": f"Project '{name}' deleted successfully"}