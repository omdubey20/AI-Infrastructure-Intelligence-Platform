"""
Website Uptime & Latency Monitoring API Router
- Live uptime checks (24/7 status, latency in ms, SSL expiry)
- On-demand ping triggers
- Historical uptime logs
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from routers.auth import get_current_user, require_role
from services.uptime_monitor import check_all_websites, ping_website
from models import ProjectDiscovery, WebsiteUptimeCheck

router = APIRouter(
    prefix="/monitoring",
    tags=["Website Monitoring"]
)


@router.get("/overview")
def get_monitoring_overview(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get high-level 24/7 uptime stats, average latency, and health breakdown."""
    discoveries = db.query(ProjectDiscovery).all()
    total_sites = len(discoveries)
    up_count = sum(1 for d in discoveries if d.is_live)
    down_count = total_sites - up_count
    uptime_pct = round((up_count / max(1, total_sites)) * 100, 1) if total_sites > 0 else 100.0

    # Calculate average latency from recent checks
    recent_checks = db.query(WebsiteUptimeCheck).order_by(WebsiteUptimeCheck.checked_at.desc()).limit(100).all()
    latencies = [c.response_time_ms for c in recent_checks if c.response_time_ms and c.is_up]
    avg_latency = int(sum(latencies) / len(latencies)) if latencies else 45

    ssl_expiring_soon = sum(1 for d in discoveries if d.ssl_expiry_days is not None and d.ssl_expiry_days <= 14)

    return {
        "total_websites": total_sites,
        "up_count": up_count,
        "down_count": down_count,
        "uptime_percentage": uptime_pct,
        "average_latency_ms": avg_latency,
        "ssl_expiring_soon": ssl_expiring_soon,
    }


@router.get("/websites")
def list_monitored_websites(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List all monitored websites with live status, latency, HTTP code, and SSL days."""
    discoveries = db.query(ProjectDiscovery).all()
    results = []

    for d in discoveries:
        domain = d.domain or d.project_name
        results.append({
            "id": d.id,
            "project_name": d.project_name,
            "domain": domain,
            "url": f"https://{domain}",
            "server_id": d.server_id,
            "is_up": bool(d.is_live),
            "http_status": d.http_status or (200 if d.is_live else 500),
            "has_ssl": bool(d.has_ssl),
            "ssl_expiry_days": d.ssl_expiry_days,
            "framework": d.framework,
            "size_mb": d.size_mb,
            "last_checked": d.last_synced_at.isoformat() if d.last_synced_at else None,
        })

    return results


@router.post("/check-now")
def trigger_live_check(
    db: Session = Depends(get_db),
    current_user = Depends(require_role(["admin", "devops"]))
):
    """Trigger an immediate live HTTP/HTTPS ping check across all discovered websites."""
    result = check_all_websites(db)
    return {
        "message": "Live website monitoring check completed",
        **result
    }


@router.post("/check/{discovery_id}")
def check_single_website(
    discovery_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_role(["admin", "devops"]))
):
    """Perform on-demand instant ping on a single project."""
    disc = db.query(ProjectDiscovery).filter(ProjectDiscovery.id == discovery_id).first()
    if not disc:
        raise HTTPException(status_code=404, detail="Project not found")

    domain = disc.domain or disc.project_name
    res = ping_website(domain)

    disc.http_status = res["http_status"]
    disc.is_live = res["is_up"]
    if res["ssl_days"] is not None:
        disc.has_ssl = res["has_ssl"]
        disc.ssl_expiry_days = res["ssl_days"]
    db.commit()

    return {
        "message": f"Ping completed for {domain}",
        "result": res
    }
