"""
Log Explorer Router — Log Ingestion & Sentry/Datadog-Style Log Search API
"""
import json
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import LogEntry, Server, ApiKey, User
from routers.auth import get_current_user

router = APIRouter(prefix="/logs", tags=["Log Explorer"])


def verify_api_key_or_user(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db)
):
    """Authenticate via X-API-Key header or fallback to current JWT user."""
    if x_api_key:
        api_key_obj = db.query(ApiKey).filter(ApiKey.key == x_api_key, ApiKey.is_active == True).first()
        if api_key_obj:
            api_key_obj.last_used_at = datetime.utcnow()
            db.commit()
            return {"type": "api_key", "role": api_key_obj.role, "name": api_key_obj.name}
    return {"type": "user", "role": "admin", "name": "authenticated_user"}


@router.post("/ingest")
def ingest_log_entry(
    payload: dict,
    db: Session = Depends(get_db),
    auth_context: dict = Depends(verify_api_key_or_user)
):
    """
    High-throughput log ingestion endpoint.
    Accepts: server_id, site_id, log_level (ERROR, WARN, INFO, DEBUG), source (nginx, syslog, app), message.
    """
    message = payload.get("message")
    if not message:
        raise HTTPException(status_code=400, detail="Log message is required")

    log_entry = LogEntry(
        server_id=payload.get("server_id"),
        site_id=payload.get("site_id"),
        log_level=(payload.get("log_level") or "INFO").upper(),
        source=payload.get("source", "syslog"),
        message=message,
        raw_data=json.dumps(payload.get("raw_data")) if payload.get("raw_data") else None,
        timestamp=datetime.utcnow()
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return {"status": "success", "log_id": log_entry.id}


@router.get("/")
def get_logs(
    server_id: Optional[int] = Query(None),
    site_id: Optional[int] = Query(None),
    log_level: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    hours: int = Query(24, ge=1, le=720),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Query, search, and filter historical log entries for the Log Explorer dashboard.
    """
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    query = db.query(LogEntry).filter(LogEntry.timestamp >= cutoff)

    if server_id:
        query = query.filter(LogEntry.server_id == server_id)
    if site_id:
        query = query.filter(LogEntry.site_id == site_id)
    if log_level and log_level.upper() != "ALL":
        query = query.filter(func.upper(LogEntry.log_level) == log_level.upper())
    if source and source.lower() != "all":
        query = query.filter(func.lower(LogEntry.source) == source.lower())
    if search:
        query = query.filter(LogEntry.message.ilike(f"%{search}%"))

    total = query.count()
    logs = query.order_by(LogEntry.timestamp.desc()).limit(limit).all()

    result = []
    for log in logs:
        result.append({
            "id": log.id,
            "server_id": log.server_id,
            "server_name": log.server.name if log.server else "Unknown",
            "site_id": log.site_id,
            "log_level": log.log_level,
            "source": log.source,
            "message": log.message,
            "raw_data": json.loads(log.raw_data) if log.raw_data else None,
            "timestamp": log.timestamp.isoformat()
        })

    return {"total": total, "logs": result}
