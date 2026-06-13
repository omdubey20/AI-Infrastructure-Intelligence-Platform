from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from routers.auth import get_current_user
import models

router = APIRouter(prefix="/projects", tags=["Projects"])


def serialize_project(project):
    server_name = None
    if getattr(project, "server", None):
        server_name = project.server.name

    return {
        "id": project.id,
        "name": project.project_name,
        "server_id": project.server_id,
        "server_name": server_name,
        "dns_points_here": project.dns_points_here,
        "web_config_active": project.web_config_active,
        "risk_score": project.risk_score,
    }


@router.get("/")
def get_all_projects(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    projects = db.query(models.ProjectDiscovery).all()
    return [serialize_project(p) for p in projects]


@router.get("/duplicates")
def get_duplicate_projects(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    projects = db.query(models.ProjectDiscovery).all()
    counts = {}

    for p in projects:
        counts[p.project_name] = counts.get(p.project_name, 0) + 1

    duplicates = [p for p in projects if counts[p.project_name] > 1]
    return [serialize_project(p) for p in duplicates]


@router.get("/server/{server_id}")
def get_projects_by_server(
    server_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    projects = db.query(models.ProjectDiscovery).filter(
        models.ProjectDiscovery.server_id == server_id
    ).all()
    return [serialize_project(p) for p in projects]


@router.get("/{project_id}")
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    project = db.query(models.ProjectDiscovery).filter(
        models.ProjectDiscovery.id == project_id
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return serialize_project(project)


@router.delete("/{project_id}")
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    project = db.query(models.ProjectDiscovery).filter(
        models.ProjectDiscovery.id == project_id
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(project)
    db.commit()

    return {"message": f"Project '{project.project_name}' deleted successfully"}