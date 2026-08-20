"""
Dashboard Stats Router — Real-time metrics from DB
All values trace back to SSH, WHM API, agent telemetry, or database queries. Never estimated.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import Server, ProjectDiscovery, Alert
from services.risk_engine import calculate_server_risk
from routers.auth import get_current_user

router = APIRouter(prefix="/stats", tags=["Stats"])


def _generate_server_insights(s) -> list:
    """Generate quick inline AI hints for the dashboard server card."""
    hints = []
    if (s.cpu_usage or 0) >= 85:
        hints.append({"type": "critical", "msg": f"CPU at {s.cpu_usage}% — investigate load"})
    elif (s.cpu_usage or 0) >= 70:
        hints.append({"type": "warning", "msg": f"CPU at {s.cpu_usage}% — monitor trend"})
    if (s.memory_usage or 0) >= 85:
        hints.append({"type": "critical", "msg": f"RAM at {s.memory_usage}% — possible leak"})
    if (s.disk_usage or 0) >= 85:
        hints.append({"type": "critical", "msg": f"Disk at {s.disk_usage}% — free space urgently"})
    if (s.ssl_expiry_days or 999) <= 30:
        hints.append({"type": "warning", "msg": f"SSL expires in {s.ssl_expiry_days} days"})
    if getattr(s, "firewall_status", None) in ("inactive", "disabled", "unknown"):
        hints.append({"type": "warning", "msg": "No active firewall detected"})
    if getattr(s, "agent_installed", False) and getattr(s, "status", "") == "agent_offline":
        hints.append({"type": "critical", "msg": "Agent offline — no telemetry received"})
    if not hints:
        hints.append({"type": "info", "msg": "Server operating within normal parameters"})
    return hints


@router.get("/dashboard")
def dashboard_stats(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    total_servers = db.query(Server).count()
    total_projects = db.query(ProjectDiscovery).count()
    servers = db.query(Server).all()
    discoveries = db.query(ProjectDiscovery).all()

    for server in servers:
        server.risk_score = calculate_server_risk(server)

    healthy_servers  = sum(1 for s in servers if (s.risk_score or 0) < 30)
    warning_servers  = sum(1 for s in servers if 30 <= (s.risk_score or 0) < 60)
    critical_servers = sum(1 for s in servers if (s.risk_score or 0) >= 60)

    top_risk_servers = sorted(servers, key=lambda x: x.risk_score or 0, reverse=True)[:5]

    live_projects      = sum(1 for d in discoveries if getattr(d, "is_live", False))
    duplicate_projects = sum(1 for d in discoveries if getattr(d, "is_duplicate", False))

    # Alert counts
    open_alerts = db.query(Alert).filter(Alert.is_resolved == False).count()

    # Uptime status metrics
    live_site_ids = [d.id for d in discoveries if getattr(d, "is_live", False)]
    uptime_monitors = len(live_site_ids)
    uptime_up = 0
    uptime_down = 0
    uptime_pending = 0

    if live_site_ids:
        from models import UptimeCheck
        from sqlalchemy import func

        latest_subq = (
            db.query(
                UptimeCheck.site_id,
                func.max(UptimeCheck.id).label("max_id")
            )
            .filter(UptimeCheck.site_id.in_(live_site_ids))
            .group_by(UptimeCheck.site_id)
            .subquery()
        )

        latest_checks = (
            db.query(UptimeCheck)
            .join(latest_subq, UptimeCheck.id == latest_subq.c.max_id)
            .all()
        )

        checked_site_ids = set()
        for check in latest_checks:
            checked_site_ids.add(check.site_id)
            if check.is_up:
                uptime_up += 1
            else:
                uptime_down += 1

        uptime_pending = len(live_site_ids) - len(checked_site_ids)

    server_breakdown = {}
    for d in discoveries:
        sid = d.server_id
        if sid not in server_breakdown:
            server_breakdown[sid] = 0
        server_breakdown[sid] += 1

    return {
        "total_servers":      total_servers,
        "total_projects":     total_projects,
        "live_projects":      live_projects,
        "duplicate_projects": duplicate_projects,
        "open_alerts":        open_alerts,
        "uptime_monitors":    uptime_monitors,
        "uptime_up":          uptime_up,
        "uptime_down":        uptime_down,
        "uptime_pending":     uptime_pending,
        "healthy_servers":    healthy_servers,
        "warning_servers":    warning_servers,
        "critical_servers":   critical_servers,
        "top_risk_servers": [
            {
                "id":             s.id,
                "name":           s.name,
                "ip_address":     s.ip_address,
                "environment":    s.environment,
                "risk_score":     s.risk_score or 0,
                "status":         s.status,
                "cpu_usage":      s.cpu_usage or 0,
                "memory_usage":   s.memory_usage or 0,
                "disk_usage":     s.disk_usage or 0,
                "uptime_days":    s.uptime_days or 0,
                "load_avg_1":     getattr(s, "load_avg_1", 0.0) or 0.0,
                "data_source":    s.data_source or "estimated",
                "agent_installed": getattr(s, "agent_installed", False),
                "last_scanned_at": s.last_scanned_at.isoformat() if s.last_scanned_at else None,
                "projects_count": server_breakdown.get(s.id, 0),
                "insights":       _generate_server_insights(s),
            }
            for s in top_risk_servers
        ],
        "server_project_breakdown": [
            {"server_id": sid, "count": cnt}
            for sid, cnt in server_breakdown.items()
        ],
    }