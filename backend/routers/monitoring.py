"""
Monitoring Router — Website Uptime Monitoring API
Ultra-fast bulk queries for fleet-wide uptime status and history.
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models import ProjectDiscovery, UptimeCheck, Server
from routers.auth import get_current_user

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


@router.get("/status")
def get_monitoring_status(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get current up/down status for all monitored sites (ultra-fast bulk aggregation)."""
    # 1. Fetch all live projects with domains in 1 single query
    sites = db.query(ProjectDiscovery).options(
        joinedload(ProjectDiscovery.server)
    ).filter(
        ProjectDiscovery.domain.isnot(None),
        ProjectDiscovery.domain != "",
        ProjectDiscovery.is_live == True,
    ).all()

    if not sites:
        return []

    site_ids = [s.id for s in sites]

    # 2. Fetch all checks in last 24h in 1 single query
    cutoff_24h = datetime.utcnow() - timedelta(hours=24)
    recent_checks = db.query(UptimeCheck).filter(
        UptimeCheck.site_id.in_(site_ids),
        UptimeCheck.checked_at >= cutoff_24h
    ).order_by(UptimeCheck.checked_at.desc()).all()

    # Aggregate in memory by site_id (sub-millisecond)
    checks_by_site = {}
    for c in recent_checks:
        if c.site_id not in checks_by_site:
            checks_by_site[c.site_id] = []
        checks_by_site[c.site_id].append(c)

    result = []
    for site in sites:
        site_checks = checks_by_site.get(site.id, [])
        latest = site_checks[0] if site_checks else None

        total_checks = len(site_checks)
        up_checks = sum(1 for c in site_checks if c.is_up)
        uptime_pct = round((up_checks / total_checks * 100), 2) if total_checks > 0 else None

        valid_rts = [c.response_time_ms for c in site_checks if c.is_up and c.response_time_ms is not None]
        avg_rt = round(sum(valid_rts) / len(valid_rts)) if valid_rts else None

        server_name = site.server.name if site.server else "Unknown"

        result.append({
            "id": site.id,
            "domain": site.domain,
            "url": f"https://{site.domain}",
            "server_id": site.server_id,
            "server_name": server_name,
            "is_up": latest.is_up if latest else None,
            "http_status": latest.http_status if latest else None,
            "response_time_ms": latest.response_time_ms if latest else None,
            "ssl_valid": latest.ssl_valid if latest else None,
            "ssl_expiry_days": latest.ssl_expiry_days if latest else None,
            "last_checked": latest.checked_at.isoformat() if latest else None,
            "error_message": latest.error_message if latest and not latest.is_up else None,
            "uptime_24h": uptime_pct,
            "avg_response_ms": avg_rt,
            "total_checks_24h": total_checks,
        })

    return result


@router.get("/history/{site_id}")
def get_uptime_history(
    site_id: int,
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get time-series uptime check data for a site."""
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    checks = db.query(UptimeCheck).filter(
        UptimeCheck.site_id == site_id,
        UptimeCheck.checked_at >= cutoff,
    ).order_by(UptimeCheck.checked_at.asc()).all()

    return [
        {
            "checked_at": c.checked_at.isoformat(),
            "is_up": c.is_up,
            "http_status": c.http_status,
            "response_time_ms": c.response_time_ms,
            "error_message": c.error_message,
        }
        for c in checks
    ]


@router.get("/summary")
def get_monitoring_summary(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get aggregate monitoring summary stats."""
    total_sites = db.query(ProjectDiscovery).filter(
        ProjectDiscovery.domain.isnot(None),
        ProjectDiscovery.domain != "",
        ProjectDiscovery.is_live == True,
    ).count()

    cutoff = datetime.utcnow() - timedelta(minutes=5)
    recent_checks = db.query(UptimeCheck).filter(
        UptimeCheck.checked_at >= cutoff
    ).order_by(UptimeCheck.checked_at.desc()).all()

    latest_by_site = {}
    for c in recent_checks:
        if c.site_id not in latest_by_site:
            latest_by_site[c.site_id] = c

    sites_up = sum(1 for c in latest_by_site.values() if c.is_up)
    sites_down = sum(1 for c in latest_by_site.values() if not c.is_up)

    return {
        "total_monitored": total_sites,
        "sites_up": sites_up,
        "sites_down": sites_down,
        "last_check_count": len(latest_by_site),
    }
