from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.orm import Session

from database import get_db

from models import Server

from services.server_scanner import scan_server_projects

router = APIRouter(
    prefix="/discovery",
    tags=["Discovery"]
)


@router.post("/scan")
def scan_all_servers(
    db: Session = Depends(get_db)
):

    servers = db.query(Server).all()

    for server in servers:
        scan_server_projects(
            db,
            server
        )

    return {
        "message": "Discovery completed",
        "servers_scanned": len(servers)
    }