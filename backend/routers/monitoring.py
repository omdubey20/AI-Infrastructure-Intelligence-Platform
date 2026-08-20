"""
Monitoring Router — Website Uptime Monitoring API
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from sqlalchemy.orm import Session, joinedload
from database import get_db
from models import ProjectDiscovery, UptimeCheck, Server
from routers.auth import get_current_user, require_role

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


@router.get("/status")
def get_monitoring_status(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get current up/down status for all monitored sites (ultra-fast bulk load)."""
    # 1. Load all live sites with server in ONE query
    sites = db.query(ProjectDiscovery).options(joinedload(ProjectDiscovery.server)).filter(
        ProjectDiscovery.domain.isnot(None),
        ProjectDiscovery.domain != "",
        ProjectDiscovery.is_live == True,
    ).all()

    if not sites:
        return []

    site_ids = [s.id for s in sites]

    # 2. Fetch latest check for each site using SQL max(id) subquery
    latest_subquery = db.query(
        UptimeCheck.site_id,
        func.max(UptimeCheck.id).label("max_id")
    ).filter(UptimeCheck.site_id.in_(site_ids)).group_by(UptimeCheck.site_id).subquery()

    latest_checks = db.query(UptimeCheck).join(
        latest_subquery, UptimeCheck.id == latest_subquery.c.max_id
    ).all()
    latest_by_site = {c.site_id: c for c in latest_checks}

    # 3. Compute 24h stats directly in SQL database engine
    cutoff_24h = datetime.utcnow() - timedelta(hours=24)
    stats_query = db.query(
        UptimeCheck.site_id,
        func.count(UptimeCheck.id).label("total"),
        func.sum(case((UptimeCheck.is_up == True, 1), else_=0)).label("up"),
        func.avg(UptimeCheck.response_time_ms).label("avg_rt")
    ).filter(
        UptimeCheck.site_id.in_(site_ids),
        UptimeCheck.checked_at >= cutoff_24h
    ).group_by(UptimeCheck.site_id).all()

    stats_by_site = {}
    for row in stats_query:
        tot = row[1] or 0
        up_cnt = row[2] or 0
        avg_rt = round(float(row[3])) if row[3] is not None else None
        pct = round((up_cnt / tot * 100), 2) if tot > 0 else None
    result = []
    for site in sites:
        latest = latest_by_site.get(site.id)
        st = stats_by_site.get(site.id, {"total": 0, "up": 0, "pct": None, "avg_rt": None})
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
            "uptime_24h": st["pct"],
            "avg_response_ms": st["avg_rt"],
            "total_checks_24h": st["total"],
        })

    return result


@router.post("/check-now")
def trigger_uptime_checks_now(
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin", "devops"]))
):
    """Trigger immediate background execution of all website uptime checks."""
    import threading
    from services.uptime_monitor import run_uptime_checks

    def _run_bg():
        db_session = next(get_db())
        try:
            run_uptime_checks(db_session)
        finally:
            db_session.close()

    threading.Thread(target=_run_bg, daemon=True).start()
    return {"message": "Instant uptime health check launched across all monitored sites."}


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

    cutoff = datetime.utcnow() - timedelta(hours=24)
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
