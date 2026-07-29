"""
Servers Router
Provides CRUD management, credentials update, connection testing, discovery scans, and server metrics.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
import models
from models import Server, ProjectDiscovery, ScanJob
from database import get_db
from routers.auth import require_role, get_current_user
from routers.audit import create_audit_entry
from services.credential_encryption import encrypt_credential, decrypt_credential
from services.server_scanner import scan_server_projects

router = APIRouter(prefix="/servers", tags=["Servers"])


class ServerCreate(BaseModel):
    name: str
    ip_address: str
    environment: str = "production"
    description: Optional[str] = None
    ssh_port: Optional[int] = 22
    ssh_username: Optional[str] = "root"
    ssh_password: Optional[str] = None
    ssh_private_key: Optional[str] = None
    whm_host: Optional[str] = None
    whm_port: Optional[int] = 2087
    whm_token: Optional[str] = None


class ServerUpdate(BaseModel):
    name: Optional[str] = None
    environment: Optional[str] = None
    description: Optional[str] = None
    ssh_port: Optional[int] = None
    ssh_username: Optional[str] = None
    ssh_password: Optional[str] = None
    ssh_private_key: Optional[str] = None
    whm_host: Optional[str] = None
    whm_port: Optional[int] = None
    whm_token: Optional[str] = None


class ServerCredentialsUpdate(BaseModel):
    ssh_port: Optional[int] = None
    ssh_username: Optional[str] = None
    ssh_password: Optional[str] = None
    ssh_private_key: Optional[str] = None
    whm_host: Optional[str] = None
    whm_port: Optional[int] = None
    whm_token: Optional[str] = None


@router.get("/")
def list_servers(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    servers = db.query(Server).all()
    results = []
    for s in servers:
        p_count = db.query(ProjectDiscovery).filter(ProjectDiscovery.server_id == s.id).count()
        results.append({
            "id": s.id,
            "name": s.name,
            "ip_address": s.ip_address,
            "environment": s.environment,
            "status": s.status,
            "description": s.description,
            "created_at": s.created_at,
            "cpu_usage": s.cpu_usage or 0,
            "memory_usage": s.memory_usage or 0,
            "disk_usage": s.disk_usage or 0,
            "risk_score": s.risk_score or 0,
            "data_source": s.data_source or "estimated",
            "last_scanned_at": s.last_scanned_at,
            "projects_count": p_count,
            "has_ssh_creds": bool(s.ssh_password or s.ssh_private_key),
            "has_whm_creds": bool(s.whm_token)
        })
    return results


@router.get("/{server_id}")
def get_server(
    server_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    discoveries = db.query(ProjectDiscovery).filter(ProjectDiscovery.server_id == server.id).all()

    return {
        "id": server.id,
        "name": server.name,
        "ip_address": server.ip_address,
        "environment": server.environment,
        "status": server.status,
        "description": server.description,
        "created_at": server.created_at,
        "hostname": getattr(server, "hostname", None),
        "os_name": getattr(server, "os_name", None),
        "os_version": getattr(server, "os_version", None),
        "kernel": getattr(server, "kernel", None),
        "architecture": getattr(server, "architecture", None),
        "cpu_cores": getattr(server, "cpu_cores", None),
        "ram_total_gb": getattr(server, "ram_total_gb", 0.0),
        "disk_total_gb": getattr(server, "disk_total_gb", 0.0),
        "cpu_usage": server.cpu_usage or 0,
        "memory_usage": server.memory_usage or 0,
        "disk_usage": server.disk_usage or 0,
        "load_avg_1": getattr(server, "load_avg_1", 0.0),
        "load_avg_5": getattr(server, "load_avg_5", 0.0),
        "uptime_days": server.uptime_days or 0,
        "error_count": server.error_count or 0,
        "risk_score": server.risk_score or 0,
        "web_server": getattr(server, "web_server", None),
        "db_engines": getattr(server, "db_engines", None),
        "docker_installed": getattr(server, "docker_installed", False),
        "docker_containers_running": getattr(server, "docker_containers_running", 0),
        "data_source": server.data_source,
        "last_scanned_at": server.last_scanned_at,
        "projects_count": len(discoveries),
        "projects": [
            {
                "id": p.id,
                "name": p.project_name,
                "domain": p.domain,
                "path": p.project_path,
                "framework": p.framework,
                "risk_score": p.risk_score,
                "is_live": p.is_live,
                "is_inactive": p.is_inactive,
                "status": "suspended" if p.is_inactive else "active"
            }
            for p in discoveries
        ]
    }



@router.post("/", status_code=status.HTTP_201_CREATED)
def create_server(
    server: ServerCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin", "devops"]))
):
    existing = db.query(Server).filter(Server.ip_address == server.ip_address).first()
    if existing:
        raise HTTPException(status_code=400, detail="Server with this IP already exists")

    data = server.model_dump()
    if data.get("ssh_password"):
        data["ssh_password"] = encrypt_credential(data["ssh_password"])
    if data.get("ssh_private_key"):
        data["ssh_private_key"] = encrypt_credential(data["ssh_private_key"])
    if data.get("whm_token"):
        data["whm_token"] = encrypt_credential(data["whm_token"])

    new_server = Server(**data)
    db.add(new_server)
    db.commit()
    db.refresh(new_server)

    create_audit_entry(db, action="create_server", entity_type="server", entity_id=new_server.id, entity_name=new_server.name, user_id=current_user.id)

    # Immediately trigger scan
    try:
        scan_server_projects(db, new_server)
    except Exception as e:
        logger.warning(f"Initial scan notice for {new_server.name}: {e}")

    return {
        "message": f"Server '{new_server.name}' created and scanned successfully",
        "id": new_server.id,
        "ip_address": new_server.ip_address
    }


@router.put("/{server_id}/credentials")
def update_credentials(
    server_id: int,
    creds: ServerCredentialsUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin", "devops"]))
):
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    if creds.ssh_port is not None: server.ssh_port = creds.ssh_port
    if creds.ssh_username is not None: server.ssh_username = creds.ssh_username
    if creds.ssh_password: server.ssh_password = encrypt_credential(creds.ssh_password)
    if creds.ssh_private_key: server.ssh_private_key = encrypt_credential(creds.ssh_private_key)
    if creds.whm_host is not None: server.whm_host = creds.whm_host
    if creds.whm_port is not None: server.whm_port = creds.whm_port
    if creds.whm_token: server.whm_token = encrypt_credential(creds.whm_token)

    db.commit()

    # Trigger scan with new credentials
    scan_result = scan_server_projects(db, server)
    create_audit_entry(db, action="update_credentials", entity_type="server", entity_id=server.id, entity_name=server.name, user_id=current_user.id)

    return {
        "message": "Credentials updated and server re-scanned successfully",
        "server_id": server.id,
        "scan_result": scan_result
    }


@router.post("/{server_id}/scan")
def trigger_scan(
    server_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin", "devops"]))
):
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    result = scan_server_projects(db, server)
    create_audit_entry(db, action="scan_server", entity_type="server", entity_id=server.id, entity_name=server.name, user_id=current_user.id)

    return {
        "message": "Discovery completed",
        "server_id": server.id,
        "server_name": server.name,
        **result
    }


@router.delete("/{server_id}")
def delete_server(
    server_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin", "devops"]))
):
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    name = server.name

    # Correctly extract integer IDs
    proj_rows = db.query(ProjectDiscovery.id).filter(ProjectDiscovery.server_id == server_id).all()
    proj_ids = [p[0] for p in proj_rows]

    if proj_ids:
        db.query(ProjectDiscovery).filter(ProjectDiscovery.duplicate_of_id.in_(proj_ids)).update({ProjectDiscovery.duplicate_of_id: None}, synchronize_session=False)
        db.query(models.AIInsight).filter(models.AIInsight.project_id.in_(proj_ids)).delete(synchronize_session=False)

    db.query(models.AIInsight).filter(models.AIInsight.server_id == server_id).delete(synchronize_session=False)
    db.query(models.ScanJob).filter(models.ScanJob.server_id == server_id).delete(synchronize_session=False)
    db.query(models.HealthSnapshot).filter(models.HealthSnapshot.server_id == server_id).delete(synchronize_session=False)
    db.query(models.Alert).filter(models.Alert.server_id == server_id).delete(synchronize_session=False)
    db.query(models.Project).filter(models.Project.server_id == server_id).delete(synchronize_session=False)
    db.query(ProjectDiscovery).filter(ProjectDiscovery.server_id == server_id).delete(synchronize_session=False)

    db.delete(server)
    db.commit()


    # Clean up any leftover orphan project records from deleted servers
    active_ids = [s.id for s in db.query(Server.id).all()]
    if active_ids:
        db.query(ProjectDiscovery).filter(~ProjectDiscovery.server_id.in_(active_ids)).delete(synchronize_session=False)
    else:
        db.query(ProjectDiscovery).delete(synchronize_session=False)
    db.commit()

    create_audit_entry(db, action="delete_server", entity_type="server", entity_id=server_id, entity_name=name, user_id=current_user.id if current_user else None)

    return {"message": f"Server '{name}' deleted successfully"}