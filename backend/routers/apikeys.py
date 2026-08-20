"""
API Keys Management Router — Granular AuthGuard Key Management API
"""
import secrets
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import ApiKey
from routers.auth import get_current_user, require_role

router = APIRouter(prefix="/auth/api-keys", tags=["API Keys AuthGuard"])


@router.get("/")
def list_api_keys(
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin", "devops"]))
):
    """List all configured API Keys."""
    keys = db.query(ApiKey).order_by(ApiKey.created_at.desc()).all()
    return [
        {
            "id": k.id,
            "name": k.name,
            "key_preview": f"{k.key[:8]}...{k.key[-4:]}",
            "role": k.role,
            "is_active": k.is_active,
            "created_at": k.created_at.isoformat() if k.created_at else None,
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
        }
        for k in keys
    ]


@router.post("/")
def create_api_key(
    payload: dict,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin"]))
):
    """Generate a new secure API Key for remote agent / telemetry ingestion."""
    name = payload.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="API Key name is required")

    role = payload.get("role", "ingest")
    if role not in ("ingest", "read", "admin"):
        role = "ingest"

    raw_key = f"infrain_sk_{secrets.token_urlsafe(32)}"
    api_key_obj = ApiKey(
        name=name,
        key=raw_key,
        role=role,
        is_active=True,
        created_at=datetime.utcnow()
    )
    db.add(api_key_obj)
    db.commit()
    db.refresh(api_key_obj)

    return {
        "message": "API key generated successfully. Save this secret key now as it will not be displayed again.",
        "id": api_key_obj.id,
        "name": api_key_obj.name,
        "api_key": raw_key,
        "role": api_key_obj.role
    }


@router.delete("/{key_id}")
def revoke_api_key(
    key_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin"]))
):
    """Revoke/Delete an API key."""
    api_key_obj = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if not api_key_obj:
        raise HTTPException(status_code=404, detail="API key not found")

    db.delete(api_key_obj)
    db.commit()
    return {"message": f"API key '{api_key_obj.name}' revoked successfully"}
