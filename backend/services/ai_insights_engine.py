"""
AI Insights Engine
Generates intelligent infrastructure, security, optimization, duplicate, and cleanup insights.
"""
import logging
from datetime import datetime
from models import AIInsight, Server, ProjectDiscovery

logger = logging.getLogger(__name__)


def generate_all_insights(db) -> list:
    """
    Analyzes all servers and project discoveries, updates AIInsight table,
    and returns generated insights.
    """
    servers = db.query(Server).all()
    discoveries = db.query(ProjectDiscovery).all()

    # Clear old insights and regenerate fresh ones
    db.query(AIInsight).delete()

    insights = []

    # 1. Server-level insights
    for s in servers:
        # High CPU
        if (s.cpu_usage or 0) >= 85:
            insight = AIInsight(
                server_id=s.id,
                category="resource",
                severity="critical",
                title=f"High CPU utilization on {s.name}",
                description=f"CPU usage is at {s.cpu_usage}%, exceeding the 85% safety threshold.",
                recommendation="Scale CPU resources or rebalance container workloads to secondary web nodes."
            )
            db.add(insight)
            insights.append(insight)

        # High Memory
        if (s.memory_usage or 0) >= 80:
            insight = AIInsight(
                server_id=s.id,
                category="resource",
                severity="warning",
                title=f"Memory pressure on {s.name}",
                description=f"RAM usage is at {s.memory_usage}%. System may experience swap thrashing.",
                recommendation="Investigate memory leaks or upgrade RAM allocation."
            )
            db.add(insight)
            insights.append(insight)

        # High Disk
        if (s.disk_usage or 0) >= 85:
            insight = AIInsight(
                server_id=s.id,
                category="resource",
                severity="critical",
                title=f"Disk space nearly full on {s.name}",
                description=f"Disk usage reached {s.disk_usage}%. Storage exhaustion imminent.",
                recommendation="Clean up log archives, remove duplicate project builds, or expand disk volume."
            )
            db.add(insight)
            insights.append(insight)

        # SSL Expiring
        if s.ssl_expiry_days is not None and s.ssl_expiry_days <= 30:
            insight = AIInsight(
                server_id=s.id,
                category="ssl",
                severity="warning" if s.ssl_expiry_days > 7 else "critical",
                title=f"SSL certificate expiring in {s.ssl_expiry_days} days on {s.name}",
                description=f"TLS certificate for hosted domains expires in {s.ssl_expiry_days} days.",
                recommendation="Run certbot renewal or re-issue SSL certificate via WHM/cPanel."
            )
            db.add(insight)
            insights.append(insight)

        # Security: No Firewall
        if getattr(s, "firewall_status", None) in ("inactive", "disabled"):
            insight = AIInsight(
                server_id=s.id,
                category="security",
                severity="warning",
                title=f"Firewall disabled on {s.name}",
                description="Server firewall is inactive or disabled, exposing all open ports.",
                recommendation="Enable UFW or firewall-cmd and configure strict inbound security rules."
            )
            db.add(insight)
            insights.append(insight)

    # 2. Project-level insights
    duplicates = [d for d in discoveries if d.is_duplicate]
    if duplicates:
        insight = AIInsight(
            category="duplicate",
            severity="warning",
            title=f"Detected {len(duplicates)} duplicate project deployment(s)",
            description=f"{len(duplicates)} project copies were identified across servers wasting storage.",
            recommendation="Review the Duplicates page to archive or delete non-production instances."
        )
        db.add(insight)
        insights.append(insight)

    inactives = [d for d in discoveries if d.is_inactive]
    if inactives:
        insight = AIInsight(
            category="inactive",
            severity="info",
            title=f"Found {len(inactives)} project(s) unused for >3 years",
            description=f"{len(inactives)} deployments have not been modified or accessed in over 1,095 days.",
            recommendation="Approve cleanup actions on the Inactive Projects page to free up disk space."
        )
        db.add(insight)
        insights.append(insight)

    db.commit()
    return insights
