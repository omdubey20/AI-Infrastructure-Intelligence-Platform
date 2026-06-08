from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from routers.auth import get_current_user
import models, schemas
from typing import List
from datetime import datetime, timedelta

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("/", response_model=List[schemas.ProjectOut])
def get_all_projects(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return db.query(models.Project).all()


@router.get("/duplicates", response_model=List[schemas.ProjectOut])
def get_duplicate_projects(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    projects = db.query(models.Project).all()
    name_count = {}
    for p in projects:
        name_count[p.name] = name_count.get(p.name, 0) + 1
    duplicates = [p for p in projects if name_count[p.name] > 1]
    return duplicates


@router.get("/unused", response_model=List[schemas.ProjectOut])
def get_unused_projects(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    three_years_ago = datetime.utcnow() - timedelta(days=1095)
    unused = db.query(models.Project).filter(
        models.Project.last_modified < three_years_ago,
        models.Project.dns_points_here == False,
        models.Project.web_config_active == False
    ).all()
    return unused


@router.get("/server/{server_id}", response_model=List[schemas.ProjectOut])
def get_projects_by_server(server_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return db.query(models.Project).filter(models.Project.server_id == server_id).all()


@router.get("/{project_id}", response_model=schemas.ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/{project_id}/status")
def update_project_status(project_id: int, status: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.status = status
    db.commit()
    return {"message": f"Project status updated to '{status}'"}


@router.delete("/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(project)
    db.commit()
    return {"message": f"Project '{project.name}' deleted successfully"}