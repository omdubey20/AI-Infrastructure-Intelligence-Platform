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
    Analyzes all servers and project discoveries, upserts AIInsight records,
    and preserves historical resolution state without ID churn.
    """
    servers = db.query(Server).all()
    discoveries = db.query(ProjectDiscovery).all()

    existing_insights = {
        (i.server_id, i.category, i.title): i
        for i in db.query(AIInsight).all()
    }

    active_keys = set()
    result_insights = []

    def _record_insight(server_id, category, severity, title, description, recommendation, project_id=None):
        key = (server_id, category, title)
        active_keys.add(key)
        existing = existing_insights.get(key)
        if existing:
            existing.severity = severity
            existing.description = description
            existing.recommendation = recommendation
            existing.project_id = project_id or existing.project_id
            existing.is_resolved = False
            result_insights.append(existing)
        else:
            new_ins = AIInsight(
                server_id=server_id,
                project_id=project_id,
                category=category,
                severity=severity,
                title=title,
                description=description,
                recommendation=recommendation,
                is_resolved=False,
            )
            db.add(new_ins)
            result_insights.append(new_ins)

    # 1. Server-level insights
    for s in servers:
        # High CPU
        if (s.cpu_usage or 0) >= 85:
            _record_insight(
                s.id, "resource", "critical",
                f"High CPU utilization on {s.name}",
                f"CPU usage is at {s.cpu_usage}%, exceeding the 85% safety threshold.",
                "Scale CPU resources or rebalance container workloads to secondary web nodes."
            )

        # High Memory
        if (s.memory_usage or 0) >= 80:
            _record_insight(
                s.id, "resource", "warning",
                f"Memory pressure on {s.name}",
                f"RAM usage is at {s.memory_usage}%. System may experience swap thrashing.",
                "Investigate memory leaks or upgrade RAM allocation."
            )

        # High Disk
        if (s.disk_usage or 0) >= 85:
            _record_insight(
                s.id, "resource", "critical",
                f"Disk space nearly full on {s.name}",
                f"Disk usage reached {s.disk_usage}%. Storage exhaustion imminent.",
                "Clean up log archives, remove duplicate project builds, or expand disk volume."
            )

        # SSL Expiring
        if s.ssl_expiry_days is not None and s.ssl_expiry_days <= 30:
            _record_insight(
                s.id, "ssl", "warning" if s.ssl_expiry_days > 7 else "critical",
                f"SSL certificate expiring in {s.ssl_expiry_days} days on {s.name}",
                f"TLS certificate for hosted domains expires in {s.ssl_expiry_days} days.",
                "Run certbot renewal or re-issue SSL certificate via WHM/cPanel."
            )

        # Security: No Firewall
        if getattr(s, "firewall_status", None) in ("inactive", "disabled"):
            _record_insight(
                s.id, "security", "warning",
                f"Firewall disabled on {s.name}",
                "Server firewall is inactive or disabled, exposing all open ports.",
                "Enable UFW or firewall-cmd and configure strict inbound security rules."
            )

    # 2. Project-level insights
    duplicates = [d for d in discoveries if d.is_duplicate]
    if duplicates:
        _record_insight(
            None, "duplicate", "warning",
            f"Detected {len(duplicates)} duplicate project deployment(s)",
            f"{len(duplicates)} project copies were identified across servers wasting storage.",
            "Review the Duplicates page to archive or delete non-production instances."
        )

    inactives = [d for d in discoveries if d.is_inactive]
    if inactives:
        _record_insight(
            None, "inactive", "info",
            f"Found {len(inactives)} project(s) unused for >3 years",
            f"{len(inactives)} deployments have not been modified or accessed in over 1,095 days.",
            "Approve cleanup actions on the Inactive Projects page to free up disk space."
        )

    # Resolve insights that are no longer active
    for key, ins in existing_insights.items():
        if key not in active_keys and not ins.is_resolved:
            ins.is_resolved = True
            ins.resolved_at = datetime.utcnow()

    db.commit()
    return result_insights
