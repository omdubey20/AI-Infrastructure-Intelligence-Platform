import os
import paramiko
from datetime import datetime
from models import ProjectDiscovery
from services.risk_engine import calculate_server_risk


SCAN_PATHS = [
    "/var/www",
    "/var/www/html",
    "/home",
    "/opt",
    "/srv",
]

SKIP_PROJECT_NAMES = {"html", "cgi-bin", "lost+found", ""}
SKIP_PREFIXES = (
    "mail.",
    "cpanel.",
    "webmail.",
    "webdisk.",
    "cpcalendars.",
    "cpcontacts.",
    "autodiscover.",
    "ftp."
)


def run_ssh_command(client, command):
    try:
        _, stdout, _ = client.exec_command(command, timeout=10)
        return stdout.read().decode("utf-8").strip()
    except Exception:
        return ""


def connect_ssh(server):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            hostname=server.ip_address,
            port=getattr(server, "ssh_port", 22) or 22,
            username=getattr(server, "ssh_username", "root"),
            password=getattr(server, "ssh_password", None),
            timeout=10
        )
        return client
    except Exception:
        return None


def discover_projects_via_ssh(client):
    projects = []

    for path in SCAN_PATHS:
        output = run_ssh_command(
            client,
            f"find {path} -maxdepth 2 -type d 2>/dev/null | head -30"
        )
        if not output:
            continue

        for line in output.splitlines():
            line = line.strip()
            if not line or line in SCAN_PATHS:
                continue

            project_name = line.split("/")[-1].strip()
            if project_name in SKIP_PROJECT_NAMES:
                continue

            projects.append({
                "name": project_name,
                "path": line
            })

    return projects


def get_server_metrics(client):
    cpu = run_ssh_command(client, "top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | cut -d'%' -f1")
    mem = run_ssh_command(client, "free | grep Mem | awk '{print ($3/$2)*100}'")
    disk = run_ssh_command(client, "df / | tail -1 | awk '{print $5}' | tr -d '%'")
    uptime = run_ssh_command(client, "cat /proc/uptime | awk '{print int($1/86400)}'")
    errors = run_ssh_command(client, "grep -c 'ERROR' /var/log/syslog 2>/dev/null || echo 0")

    def safe_int(val, default=0):
        try:
            return int(float(val))
        except Exception:
            return default

    return {
        "cpu_usage": safe_int(cpu),
        "memory_usage": safe_int(mem),
        "disk_usage": safe_int(disk),
        "uptime_days": safe_int(uptime),
        "error_count": safe_int(errors)
    }


def check_dns(client, project_name):
    result = run_ssh_command(
        client,
        f"host {project_name} 2>/dev/null | grep 'has address' | head -1"
    )
    return bool(result)


def check_web_config(client, project_path):
    nginx = run_ssh_command(
        client,
        f"grep -r '{project_path}' /etc/nginx/sites-enabled/ 2>/dev/null | head -1"
    )
    apache = run_ssh_command(
        client,
        f"grep -r '{project_path}' /etc/apache2/sites-enabled/ 2>/dev/null | head -1"
    )
    return bool(nginx or apache)


def upsert_discovery(
    db,
    server_id,
    project_name,
    project_path,
    size_mb,
    dns_points_here,
    web_config_active,
    risk_score,
    data_source
):
    existing = (
        db.query(ProjectDiscovery)
        .filter(
            ProjectDiscovery.server_id == server_id,
            ProjectDiscovery.project_name == project_name
        )
        .first()
    )

    if existing:
        existing.project_path = project_path
        existing.size_mb = size_mb
        existing.dns_points_here = dns_points_here
        existing.web_config_active = web_config_active
        existing.risk_score = risk_score
        existing.data_source = data_source
        return existing

    discovery = ProjectDiscovery(
        server_id=server_id,
        project_name=project_name,
        project_path=project_path,
        size_mb=size_mb,
        dns_points_here=dns_points_here,
        web_config_active=web_config_active,
        risk_score=risk_score,
        data_source=data_source
    )
    db.add(discovery)
    return discovery


def scan_server_projects(db, server):
    client = connect_ssh(server)
    ssh_available = client is not None

    if ssh_available:
        metrics = get_server_metrics(client)

        server.cpu_usage = metrics["cpu_usage"]
        server.memory_usage = metrics["memory_usage"]
        server.disk_usage = metrics["disk_usage"]
        server.uptime_days = metrics["uptime_days"]
        server.error_count = metrics["error_count"]
        server.risk_score = calculate_server_risk(server)
        server.status = "active"
        server.data_source = "ssh"
        server.last_scanned_at = datetime.utcnow()
        db.commit()

        raw_projects = discover_projects_via_ssh(client)

        for proj in raw_projects:
            dns_live = check_dns(client, proj["name"])
            web_active = check_web_config(client, proj["path"])

            size_raw = run_ssh_command(
                client,
                f"du -sm {proj['path']} 2>/dev/null | awk '{{print $1}}'"
            )

            try:
                size_mb = int(size_raw)
            except Exception:
                size_mb = 0

            upsert_discovery(
                db=db,
                server_id=server.id,
                project_name=proj["name"],
                project_path=proj["path"],
                size_mb=size_mb,
                dns_points_here=dns_live,
                web_config_active=web_active,
                risk_score=20,
                data_source="ssh"
            )

        db.commit()
        client.close()

    else:
        server.status = "active"
        server.data_source = "whm_estimated"
        server.last_scanned_at = datetime.utcnow()

        whm_host = getattr(server, "whm_host", None) or os.getenv("WHM_HOST")
        whm_token = getattr(server, "whm_token", None) or os.getenv("WHM_TOKEN")
        whm_port = getattr(server, "whm_port", 2087) or 2087

        real_disk = server.disk_usage or 0

        if whm_host and whm_token:
            try:
                from services.whm_service import get_whm_accounts_for_server
                accts = get_whm_accounts_for_server(whm_host, whm_token, whm_port)

                if accts:
                    disk_str = accts[0].get("diskused", "0M").replace("M", "").replace("G", "000")
                    disk_limit_str = accts[0].get("disklimit", "unlimited")

                    if disk_limit_str != "unlimited":
                        used = float(disk_str)
                        limit = float(disk_limit_str.replace("M", "").replace("G", "000"))
                        real_disk = int((used / limit) * 100) if limit > 0 else 50
                    else:
                        real_disk = 30
            except Exception:
                real_disk = server.disk_usage or 40

        disk_factor = real_disk / 100.0
        server.cpu_usage = int(15 + disk_factor * 45)
        server.memory_usage = int(20 + disk_factor * 40)
        server.disk_usage = real_disk
        server.uptime_days = server.uptime_days or 0
        server.error_count = 0
        server.risk_score = calculate_server_risk(server)
        db.commit()

        sample_projects = []

        if whm_host and whm_token:
            try:
                from services.whm_service import (
                    get_whm_accounts_for_server,
                    get_account_domains_with_creds,
                )

                accts = get_whm_accounts_for_server(whm_host, whm_token, whm_port)

                for acc in accts:
                    domains = get_account_domains_with_creds(
                        whm_host,
                        whm_token,
                        whm_port,
                        acc.get("user", "")
                    )
                    for d in domains:
                        name = d.get("name")
                        path = d.get("path", "/home/business/public_html")

                        if not name:
                            continue

                        if any(name.startswith(prefix) for prefix in SKIP_PREFIXES):
                            continue

                        sample_projects.append((name, path))
            except Exception:
                sample_projects = []

        for project_name, project_path in sample_projects:
            from services.dns_checker import check_project_health

            dns_live, web_active, proj_risk = check_project_health(project_name, project_path)

            upsert_discovery(
                db=db,
                server_id=server.id,
                project_name=project_name,
                project_path=project_path,
                size_mb=0,
                dns_points_here=dns_live,
                web_config_active=web_active,
                risk_score=proj_risk,
                data_source="whm_estimated"
            )

        db.commit()

    return {"ssh_connected": ssh_available}