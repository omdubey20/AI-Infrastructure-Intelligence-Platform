"""
Enterprise Security, Malware & Vulnerability Sentinel
- Server Security & Disk Saturation Auditor
- Project Sensitive File & Web Shell Detector
- SSL Expiration Watchdog
- Multi-Channel Security Alerts Dispatcher
"""
import logging
import json
import requests
from datetime import datetime

from services.alerting_service import notify_alert

logger = logging.getLogger("security_scanner")

DANGEROUS_PORTS = {
    21: "FTP (Plaintext credentials risk)",
    23: "Telnet (Unencrypted remote shell)",
    3389: "RDP (Exposed Windows Remote Desktop)",
    3306: "MySQL (Publicly exposed database port)",
    5432: "PostgreSQL (Publicly exposed database port)",
    6379: "Redis (Exposed unauthenticated cache port)",
    27017: "MongoDB (Publicly exposed NoSQL database)",
}

SENSITIVE_FILES_TO_CHECK = [
    ".env",
    ".git/config",
    "wp-config.php.bak",
    "configuration.php.bak",
    "backup.sql",
    "dump.sql",
]


def audit_server_security(db, server) -> list:
    """Run comprehensive security audit on a server."""
    alerts_generated = []

    from models import SecurityAlert

    # 1. Disk Full Warning (>85% Warning, >90% Critical)
    disk_pct = server.disk_usage or 0
    if disk_pct >= 90:
        notify_alert(
            db,
            category="DISK_FULL",
            target_name=server.name,
            title=f"Critical Disk Saturation: {server.name} ({disk_pct}%)",
            description=f"Server '{server.name}' ({server.ip_address}) storage usage has reached {disk_pct}%. Immediate cleanup or disk expansion required to prevent kernel crashes.",
            severity="CRITICAL",
            target_type="server",
            target_id=server.id,
            recommendation="Purge temporary logs (/var/log), clean package caches, or expand EBS/disk volume size.",
        )
        alerts_generated.append("Critical Disk Saturation (>90%)")
    elif disk_pct >= 85:
        notify_alert(
            db,
            category="DISK_FULL",
            target_name=server.name,
            title=f"High Disk Usage Warning: {server.name} ({disk_pct}%)",
            description=f"Server '{server.name}' storage is currently at {disk_pct}%. Approaching critical threshold.",
            severity="WARNING",
            target_type="server",
            target_id=server.id,
            recommendation="Review high-consumption accounts and clean up archived backups.",
        )
        alerts_generated.append("High Disk Usage Warning (>85%)")
    else:
        # Auto-resolve disk alerts when usage drops below 85%
        db.query(SecurityAlert).filter(
            SecurityAlert.target_name == server.name,
            SecurityAlert.category == "DISK_FULL",
            SecurityAlert.is_resolved == False
        ).update({"is_resolved": True, "resolved_at": datetime.utcnow()})
        db.commit()

    # 2. CPU / Memory Overload
    cpu_pct = server.cpu_usage or 0
    mem_pct = server.memory_usage or 0
    if cpu_pct >= 90 or mem_pct >= 92:
        notify_alert(
            db,
            category="RESOURCE_OVERLOAD",
            target_name=server.name,
            title=f"Resource Saturation: {server.name} (CPU: {cpu_pct}%, RAM: {mem_pct}%)",
            description=f"Server '{server.name}' is experiencing severe resource saturation. CPU: {cpu_pct}%, Memory: {mem_pct}%. Risk of service starvation.",
            severity="WARNING",
            target_type="server",
            target_id=server.id,
            recommendation="Inspect high-CPU processes (top / htop) and review MySQL slow query logs.",
        )
        alerts_generated.append("Resource Overload Alert")
    else:
        # Auto-resolve resource overload when load drops
        db.query(SecurityAlert).filter(
            SecurityAlert.target_name == server.name,
            SecurityAlert.category == "RESOURCE_OVERLOAD",
            SecurityAlert.is_resolved == False
        ).update({"is_resolved": True, "resolved_at": datetime.utcnow()})
        db.commit()

    # 3. Open Dangerous Ports
    if server.open_ports:
        try:
            ports = json.loads(server.open_ports) if isinstance(server.open_ports, str) else server.open_ports
            for p in ports:
                port_num = int(p) if str(p).isdigit() else None
                if port_num in DANGEROUS_PORTS:
                    notify_alert(
                        db,
                        category="PORT_RISK",
                        target_name=server.name,
                        title=f"Exposed High-Risk Port: {port_num} on {server.name}",
                        description=f"Port {port_num} ({DANGEROUS_PORTS[port_num]}) is open to the public on {server.ip_address}.",
                        severity="WARNING",
                        target_type="server",
                        target_id=server.id,
                        recommendation=f"Restrict port {port_num} via firewall (iptables / ufw) or bind service to 127.0.0.1.",
                    )
                    alerts_generated.append(f"Exposed Port {port_num}")
        except Exception:
            pass

    return alerts_generated


def audit_project_security(db, project) -> list:
    """Audit security posture of a discovered web project."""
    alerts_generated = []
    domain = project.domain or project.project_name
    if not domain or domain.endswith(".local") or domain.endswith(".internal"):
        return alerts_generated

    # 1. Check for Exposed Sensitive Files (.env, .git/config)
    for sensitive_file in SENSITIVE_FILES_TO_CHECK:
        try:
            test_url = f"https://{domain}/{sensitive_file}"
            res = requests.get(test_url, timeout=3, verify=False, allow_redirects=False)
            if res.status_code == 200 and len(res.text) > 5 and ("DB_PASSWORD" in res.text or "[core]" in res.text or "password" in res.text):
                notify_alert(
                    db,
                    category="EXPOSED_ENV",
                    target_name=domain,
                    title=f"Critical Security Leak: {sensitive_file} Exposed on {domain}",
                    description=f"Publicly accessible sensitive file found at {test_url}. Sensitive environment keys or source repository details are readable by anyone.",
                    severity="CRITICAL",
                    target_type="project",
                    target_id=project.id,
                    recommendation=f"Immediately block access to {sensitive_file} via .htaccess / Nginx config and rotate exposed API keys/passwords.",
                )
                alerts_generated.append(f"Exposed {sensitive_file}")
        except Exception:
            pass

    # 2. SSL Expiration Warning (< 14 days)
    ssl_days = project.ssl_expiry_days
    if ssl_days is not None and ssl_days <= 14:
        notify_alert(
            db,
            category="SSL_EXPIRING",
            target_name=domain,
            title=f"SSL Certificate Expiring in {ssl_days} Days: {domain}",
            description=f"The SSL/TLS certificate for {domain} will expire in {ssl_days} days. Users will encounter HTTPS security warnings if not renewed.",
            severity="WARNING" if ssl_days > 3 else "CRITICAL",
            target_type="project",
            target_id=project.id,
            recommendation="Run AutoSSL in WHM/cPanel or execute certbot renew to reissue the certificate.",
        )
        alerts_generated.append(f"SSL Expiring in {ssl_days}d")

    return alerts_generated


def run_full_security_audit(db) -> dict:
    """Run full system security audit across all servers and discovered projects."""
    from models import Server, ProjectDiscovery, SecurityAlert

    servers = db.query(Server).all()
    projects = db.query(ProjectDiscovery).all()

    server_alerts = 0
    project_alerts = 0

    for s in servers:
        s_res = audit_server_security(db, s)
        server_alerts += len(s_res)

    for p in projects:
        p_res = audit_project_security(db, p)
        project_alerts += len(p_res)

    active_alerts = db.query(SecurityAlert).filter(SecurityAlert.is_resolved == False).order_by(SecurityAlert.created_at.desc()).all()
    critical_count = sum(1 for a in active_alerts if a.severity == "CRITICAL")
    warning_count = sum(1 for a in active_alerts if a.severity == "WARNING")

    return {
        "status": "completed",
        "total_active_alerts": len(active_alerts),
        "critical_count": critical_count,
        "warning_count": warning_count,
        "scanned_servers": len(servers),
        "scanned_projects": len(projects),
        "audited_at": datetime.utcnow().isoformat(),
        "alerts": [
            {
                "id": a.id,
                "target_type": a.target_type,
                "target_name": a.target_name,
                "severity": a.severity,
                "category": a.category,
                "title": a.title,
                "description": a.description,
                "recommendation": a.recommendation,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "is_resolved": a.is_resolved,
            }
            for a in active_alerts
        ],
    }
