"""
Dashboard Specification Router — Section 6 API Standard Implementation
All endpoints require authentication.
- GET /api/dashboard/summary
- GET /api/accounts
- GET /api/sites
- GET /api/alerts
- PATCH /api/alerts/{id}/resolve
- GET /api/servers/{id}/history
- POST /api/servers/{id}/check-now
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
import models
from routers.auth import get_current_user, require_role
from services.server_scanner import scan_server_projects
from services.duplicate_detector import detect_duplicates
from services.inactive_detector import detect_inactive_projects
from services.ai_insights_engine import generate_all_insights

router = APIRouter(prefix="/api", tags=["Developer Spec API"])


def _safe_float_val(val):
    try:
        return float(val)
    except Exception:
        return str(val)


@router.get("/dashboard/summary")
def get_dashboard_summary(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Summary counts: servers online/offline, accounts active/suspended, sites up/down, open alerts."""
    servers = db.query(models.Server).all()
    discoveries = db.query(models.ProjectDiscovery).all()
    alerts = db.query(models.Alert).filter(models.Alert.is_resolved == False).all()

    servers_online = sum(1 for s in servers if (s.status or "active") == "active")
    servers_offline = len(servers) - servers_online

    accounts_active = sum(1 for d in discoveries if not d.is_inactive)
    accounts_suspended = sum(1 for d in discoveries if d.is_inactive)

    sites_up = sum(1 for d in discoveries if d.is_live and not d.is_inactive)
    sites_down = sum(1 for d in discoveries if not d.is_live or d.is_inactive)

    return {
        "servers_online": servers_online,
        "servers_offline": servers_offline,
        "servers_total": len(servers),
        "accounts_active": accounts_active,
        "accounts_suspended": accounts_suspended,
        "accounts_total": len(discoveries),
        "sites_up": sites_up,
        "sites_down": sites_down,
        "sites_total": len(discoveries),
        "open_alerts": len(alerts),
        "last_updated_at": datetime.utcnow().isoformat(),
    }


@router.get("/accounts")
def get_accounts(
    server_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Filterable cPanel account list per server."""
    query = db.query(models.ProjectDiscovery)
    if server_id is not None:
        query = query.filter(models.ProjectDiscovery.server_id == server_id)
    if status is not None:
        if status.lower() == "suspended":
            query = query.filter(models.ProjectDiscovery.is_inactive == True)
        elif status.lower() == "active":
            query = query.filter(models.ProjectDiscovery.is_inactive == False)

    accts = query.all()
    return [
        {
            "id": a.id,
            "server_id": a.server_id,
            "cpanel_user": a.owner or a.project_name,
            "domain": a.domain or a.project_name,
            "owner": a.owner or "root",
            "package": "standard_cpanel",
            "status": "suspended" if a.is_inactive else "active",
            "disk_used_mb": a.size_mb or 100,
            "disk_limit_mb": 5000,
            "last_synced_at": a.last_synced_at.isoformat() if a.last_synced_at else None,
        }
        for a in accts
    ]


@router.get("/sites")
def get_sites(
    server_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Filterable site health check list."""
    query = db.query(models.ProjectDiscovery)
    if server_id is not None:
        query = query.filter(models.ProjectDiscovery.server_id == server_id)
    if status is not None:
        if status.lower() == "down":
            query = query.filter((models.ProjectDiscovery.is_live == False) | (models.ProjectDiscovery.is_inactive == True))
        elif status.lower() == "up":
            query = query.filter(models.ProjectDiscovery.is_live == True, models.ProjectDiscovery.is_inactive == False)

    sites = query.all()
    return [
        {
            "id": s.id,
            "account_id": s.id,
            "server_id": s.server_id,
            "url": f"https://{s.domain}" if s.domain else f"http://{s.project_name}",
            "domain": s.domain or s.project_name,
            "framework": s.framework or "unknown",
            "http_status": 503 if s.is_inactive else (200 if s.is_live else 404),
            "response_ms": None,  # Not measured — explicitly null instead of fake value
            "ssl_expires_at": (datetime.utcnow() + timedelta(days=s.ssl_expiry_days)).date().isoformat() if s.has_ssl and s.ssl_expiry_days else None,
            "is_up": bool(s.is_live and not s.is_inactive),
            "last_checked_at": s.last_synced_at.isoformat() if s.last_synced_at else datetime.utcnow().isoformat(),
        }
        for s in sites
    ]


@router.get("/alerts")
def get_alerts(
    resolved: Optional[bool] = Query(False),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Filterable alerts list."""
    query = db.query(models.Alert)
    if resolved is not None:
        query = query.filter(models.Alert.is_resolved == resolved)

    alerts = query.order_by(models.Alert.created_at.desc()).all()

    # Fallback to AI Insights if alerts table is empty
    if not alerts and not resolved:
        insights = db.query(models.AIInsight).filter(models.AIInsight.is_resolved == False).all()
        return [
            {
                "id": i.id,
                "server_id": i.server_id,
                "site_id": i.project_id,
                "type": i.category or "service_down",
                "severity": i.severity or "warning",
                "message": f"{i.title}: {i.description}",
                "is_resolved": i.is_resolved,
                "created_at": i.created_at.isoformat(),
                "resolved_at": i.resolved_at.isoformat() if i.resolved_at else None,
            }
            for i in insights
        ]

    return [
        {
            "id": a.id,
            "server_id": a.server_id,
            "site_id": a.site_id,
            "type": a.type,
            "severity": a.severity,
            "message": a.message,
            "is_resolved": a.is_resolved,
            "created_at": a.created_at.isoformat(),
            "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
        }
        for a in alerts
    ]


@router.patch("/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Mark an alert resolved."""
    alert = db.query(models.Alert).filter(models.Alert.id == alert_id).first()
    if alert:
        alert.is_resolved = True
        alert.resolved_at = datetime.utcnow()
        db.commit()
        return {"status": "success", "alert_id": alert_id, "is_resolved": True}

    insight = db.query(models.AIInsight).filter(models.AIInsight.id == alert_id).first()
    if insight:
        insight.is_resolved = True
        insight.resolved_at = datetime.utcnow()
        db.commit()
        return {"status": "success", "alert_id": alert_id, "is_resolved": True}

    raise HTTPException(status_code=404, detail="Alert not found")


@router.post("/servers/{server_id}/check-now")
def server_check_now(
    server_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin", "devops"])),
):
    """Force an immediate poll & health check bypassing schedule."""
    server = db.query(models.Server).filter(models.Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    res = scan_server_projects(db, server)
    discoveries = db.query(models.ProjectDiscovery).filter(models.ProjectDiscovery.server_id == server_id).all()
    detect_duplicates(discoveries)
    detect_inactive_projects(discoveries)
    generate_all_insights(db)
    db.commit()

    return {
        "status": "success",
        "server_id": server_id,
        "message": f"Server {server.name} check completed",
        "projects_found": len(discoveries),
        "details": res,
    }


@router.get("/servers/{server_id}/history")
def get_server_history(
    server_id: int,
    metric: str = Query("loadavg"),
    time_span: str = Query("24h", alias="range"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Time-series metric data for charts."""
    snapshots = db.query(models.HealthSnapshot).filter(
        models.HealthSnapshot.server_id == server_id,
        models.HealthSnapshot.metric == metric
    ).order_by(models.HealthSnapshot.recorded_at.asc()).all()

    if snapshots:
        return [
            {
                "id": s.id,
                "metric": s.metric,
                "value": _safe_float_val(s.value),
                "recorded_at": s.recorded_at.isoformat(),
                "data_source": "live",
            }
            for s in snapshots
        ]

    # No snapshots — return empty with metadata explaining why
    server = db.query(models.Server).filter(models.Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    return {
        "data": [],
        "message": "No historical snapshots available yet. Data will populate after the next scan cycle.",
        "server_id": server_id,
        "metric": metric,
    }
