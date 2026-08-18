"""
Monitoring Router — Website Uptime Monitoring API
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import ProjectDiscovery, UptimeCheck, Server
from routers.auth import get_current_user

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


@router.get("/status")
def get_monitoring_status(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get current up/down status for all monitored sites."""
    # Get all live projects with domains
    sites = db.query(ProjectDiscovery).filter(
        ProjectDiscovery.domain.isnot(None),
        ProjectDiscovery.domain != "",
        ProjectDiscovery.is_live == True,
    ).all()

    result = []
    for site in sites:
        # Get latest check
        latest = db.query(UptimeCheck).filter(
            UptimeCheck.site_id == site.id
        ).order_by(UptimeCheck.checked_at.desc()).first()

        # Calculate uptime percentage (last 24h)
        cutoff_24h = datetime.utcnow() - timedelta(hours=24)
        total_checks = db.query(UptimeCheck).filter(
            UptimeCheck.site_id == site.id,
            UptimeCheck.checked_at >= cutoff_24h,
        ).count()

        up_checks = db.query(UptimeCheck).filter(
            UptimeCheck.site_id == site.id,
            UptimeCheck.checked_at >= cutoff_24h,
            UptimeCheck.is_up == True,
        ).count()

        uptime_pct = round((up_checks / total_checks * 100), 2) if total_checks > 0 else None

        # Average response time (last 24h)
        avg_rt = db.query(func.avg(UptimeCheck.response_time_ms)).filter(
            UptimeCheck.site_id == site.id,
            UptimeCheck.checked_at >= cutoff_24h,
            UptimeCheck.is_up == True,
        ).scalar()

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
            "avg_response_ms": round(avg_rt) if avg_rt else None,
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

    # Get sites with recent checks
    cutoff = datetime.utcnow() - timedelta(minutes=5)
    recent_checks = db.query(UptimeCheck).filter(
        UptimeCheck.checked_at >= cutoff
    ).all()

    # Deduplicate by site_id, keep latest
    latest_by_site = {}
    for c in recent_checks:
        if c.site_id not in latest_by_site or c.checked_at > latest_by_site[c.site_id].checked_at:
            latest_by_site[c.site_id] = c

    sites_up = sum(1 for c in latest_by_site.values() if c.is_up)
    sites_down = sum(1 for c in latest_by_site.values() if not c.is_up)

    return {
        "total_monitored": total_sites,
        "sites_up": sites_up,
        "sites_down": sites_down,
        "last_check_count": len(latest_by_site),
    }
