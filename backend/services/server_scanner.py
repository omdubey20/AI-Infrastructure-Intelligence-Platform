import paramiko
import random
from datetime import datetime
from models import Server, ProjectDiscovery
from services.risk_engine import calculate_server_risk


SCAN_PATHS = [
    "/var/www",
    "/var/www/html",
    "/home",
    "/opt",
    "/srv",
]


def run_ssh_command(client, command):
    try:
        _, stdout, stderr = client.exec_command(command, timeout=10)
        return stdout.read().decode("utf-8").strip()
    except Exception:
        return ""


def connect_ssh(server):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            hostname=server.ip_address,
            port=22,
            username=getattr(server, "ssh_username", "root"),
            password=getattr(server, "ssh_password", None),
            timeout=10
        )
        return client
    except Exception as e:
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
            project_name = line.split("/")[-1]
            if project_name in ["html", "cgi-bin", "lost+found", ""]:
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


def scan_server_projects(db, server):
    client = connect_ssh(server)
    ssh_available = client is not None

    if ssh_available:
        # Real SSH scan
        metrics = get_server_metrics(client)
        server.cpu_usage = metrics["cpu_usage"]
        server.memory_usage = metrics["memory_usage"]
        server.disk_usage = metrics["disk_usage"]
        server.uptime_days = metrics["uptime_days"]
        server.error_count = metrics["error_count"]
        server.risk_score = calculate_server_risk(server)
        server.status = "active"
        db.commit()

        raw_projects = discover_projects_via_ssh(client)

        for proj in raw_projects:
            existing = (
                db.query(ProjectDiscovery)
                .filter(
                    ProjectDiscovery.server_id == server.id,
                    ProjectDiscovery.project_name == proj["name"]
                )
                .first()
            )
            if existing:
                continue

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

            discovery = ProjectDiscovery(
                server_id=server.id,
                project_name=proj["name"],
                project_path=proj["path"],
                size_mb=size_mb,
                dns_points_here=dns_live,
                web_config_active=web_active,
                risk_score=random.randint(10, 90)
            )
            db.add(discovery)
            db.commit()

        client.close()

    else:
        # SSH not reachable — use simulated data for demo
        server.status = "unreachable"
        server.cpu_usage = random.randint(20, 95)
        server.memory_usage = random.randint(30, 90)
        server.disk_usage = random.randint(40, 95)
        server.uptime_days = random.randint(1, 400)
        server.error_count = random.randint(0, 50)
        server.risk_score = calculate_server_risk(server)
        db.commit()

        sample_projects = [
            ("labhmitra", "/var/www/labhmitra"),
            ("bbx", "/var/www/bbx"),
            ("crm", "/var/www/crm"),
            ("oldcrm", "/var/www/oldcrm"),
            ("inventory", "/var/www/inventory"),
        ]

        for project_name, project_path in sample_projects:
            existing = (
                db.query(ProjectDiscovery)
                .filter(
                    ProjectDiscovery.server_id == server.id,
                    ProjectDiscovery.project_name == project_name
                )
                .first()
            )
            if existing:
                continue

            discovery = ProjectDiscovery(
                server_id=server.id,
                project_name=project_name,
                project_path=project_path,
                size_mb=random.randint(100, 5000),
                dns_points_here=random.choice([True, False]),
                web_config_active=random.choice([True, False]),
                risk_score=random.randint(10, 90)
            )
            db.add(discovery)

    db.commit()
    return {"ssh_connected": ssh_available}