"""
Audit Log Router
Provides audit trails for every scan, API action, cleanup approval, and authentication event.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from database import get_db
from models import AuditLog
from routers.auth import get_current_user

router = APIRouter(prefix="/audit", tags=["Audit Logs"])


@router.get("/logs")
def get_audit_logs(
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)

    total = query.count()
    logs = query.order_by(AuditLog.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "logs": [
            {
                "id": l.id,
                "user_id": l.user_id,
                "action": l.action,
                "entity_type": l.entity_type,
                "entity_id": l.entity_id,
                "entity_name": l.entity_name,
                "details": l.details,
                "status": l.status,
                "created_at": l.created_at.isoformat() if l.created_at else None
            }
            for l in logs
        ]
    }


def create_audit_entry(db: Session, action: str, entity_type: str = None, entity_id: int = None, entity_name: str = None, details: str = None, user_id: int = None):
    """Utility helper to record an audit log entry."""
    try:
        log = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            details=details,
            status="success"
        )
        db.add(log)
        db.commit()
    except Exception:
        db.rollback()
