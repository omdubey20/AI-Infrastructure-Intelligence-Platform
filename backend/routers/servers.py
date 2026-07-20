from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import Server, ProjectDiscovery, ScanLog, Project
from schemas import ServerCreate, ServerOut
from routers.auth import (
    get_current_user,
    require_role
)

router = APIRouter(
    prefix="/servers",
    tags=["Servers"]
)


# =========================
# GET ALL SERVERS
# =========================

@router.get(
    "/",
    response_model=List[ServerOut]
)
def get_servers(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return db.query(Server).all()


# =========================
# CREATE SERVER
# Admin + DevOps
# =========================

@router.post(
    "/",
    response_model=ServerOut,
    status_code=status.HTTP_201_CREATED
)
def create_server(
    server: ServerCreate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_role(
            ["admin", "devops"]
        )
    )
):
    existing_server = (
        db.query(Server)
        .filter(
            Server.ip_address == server.ip_address
        )
        .first()
    )

    if existing_server:
        raise HTTPException(
            status_code=400,
            detail="Server with this IP already exists"
        )

    new_server = Server(
        **server.model_dump()
    )

    db.add(new_server)
    db.commit()
    db.refresh(new_server)

    return new_server


# =========================
# UPDATE SERVER
# Admin + DevOps
# =========================

@router.put(
    "/{server_id}",
    response_model=ServerOut
)
def update_server(
    server_id: int,
    server: ServerCreate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_role(
            ["admin", "devops"]
        )
    )
):
    existing_server = (
        db.query(Server)
        .filter(
            Server.id == server_id
        )
        .first()
    )

    if not existing_server:
        raise HTTPException(
            status_code=404,
            detail="Server not found"
        )

    duplicate_ip = (
        db.query(Server)
        .filter(
            Server.ip_address == server.ip_address,
            Server.id != server_id
        )
        .first()
    )

    if duplicate_ip:
        raise HTTPException(
            status_code=400,
            detail="Server with this IP already exists"
        )

    update_data = server.model_dump()

    for field, value in update_data.items():
        setattr(
            existing_server,
            field,
            value
        )

    db.commit()
    db.refresh(existing_server)

    return existing_server


# =========================
# DELETE SERVER
# Admin Only
# =========================

@router.delete("/{server_id}")
def delete_server(
    server_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin"]))
):
    server = (
        db.query(Server)
        .filter(Server.id == server_id)
        .first()
    )

    if not server:
        raise HTTPException(
            status_code=404,
            detail="Server not found"
        )

    db.query(ProjectDiscovery).filter(
        ProjectDiscovery.server_id == server_id
    ).delete(synchronize_session=False)

    db.query(Project).filter(
        Project.server_id == server_id
    ).delete(synchronize_session=False)

    db.query(ScanLog).filter(
        ScanLog.server_id == server_id
    ).delete(synchronize_session=False)

    db.delete(server)
    db.commit()

    return {"message": "Server deleted successfully"}