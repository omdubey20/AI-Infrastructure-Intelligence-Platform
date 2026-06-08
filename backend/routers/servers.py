from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from routers.auth import get_current_user
import models, schemas
from typing import List
from datetime import datetime

router = APIRouter(prefix="/servers", tags=["Servers"])


@router.post("/", response_model=schemas.ServerOut)
def add_server(server: schemas.ServerCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    existing = db.query(models.Server).filter(models.Server.name == server.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Server with this name already exists")
    new_server = models.Server(**server.model_dump())
    db.add(new_server)
    db.commit()
    db.refresh(new_server)
    return new_server


@router.get("/", response_model=List[schemas.ServerOut])
def get_all_servers(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return db.query(models.Server).all()


@router.get("/{server_id}", response_model=schemas.ServerOut)
def get_server(server_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    server = db.query(models.Server).filter(models.Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return server


@router.delete("/{server_id}")
def delete_server(server_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    server = db.query(models.Server).filter(models.Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    db.delete(server)
    db.commit()
    return {"message": f"Server '{server.name}' deleted successfully"}


@router.put("/{server_id}/status")
def update_server_status(server_id: int, status: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    server = db.query(models.Server).filter(models.Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    server.status = status
    server.last_scanned = datetime.utcnow()
    db.commit()
    return {"message": f"Server status updated to '{status}'"}