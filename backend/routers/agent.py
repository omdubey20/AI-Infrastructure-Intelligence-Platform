"""
Agent Router — Receives telemetry from installed server agents
"""
import logging
import os
import secrets
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Server, HealthSnapshot, Alert
from services.risk_engine import calculate_server_risk
from services.notification_service import create_and_dispatch_alert
from routers.auth import get_current_user, require_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["Agent"])

AGENT_SECRET = os.getenv("AGENT_SECRET_KEY", "infra-agent-default-key")

# Alert thresholds
DISK_WARN_THRESHOLD = 85
DISK_CRIT_THRESHOLD = 92
CPU_WARN_THRESHOLD = 85
CPU_CRIT_THRESHOLD = 95
MEM_WARN_THRESHOLD = 85
MEM_CRIT_THRESHOLD = 95


class AgentReport(BaseModel):
    api_key: str
    cpu_usage: Optional[int] = None
    memory_usage: Optional[int] = None
    disk_usage: Optional[int] = None
    load_avg_1: Optional[float] = None
    load_avg_5: Optional[float] = None
    load_avg_15: Optional[float] = None
    uptime_days: Optional[int] = None
    error_count: Optional[int] = None
    ram_total_gb: Optional[float] = None
    swap_usage: Optional[int] = None
    cpu_cores: Optional[int] = None
    cpu_model: Optional[str] = None
    hostname: Optional[str] = None
    os_name: Optional[str] = None
    os_version: Optional[str] = None
    kernel: Optional[str] = None
    architecture: Optional[str] = None
    open_ports: Optional[str] = None
    running_services: Optional[str] = None
    discovered_projects: Optional[list] = None


@router.post("/report")
def receive_agent_report(report: AgentReport, db: Session = Depends(get_db)):
    """Receive telemetry report from an installed agent."""
    # Authenticate by API key
    server = db.query(Server).filter(Server.agent_api_key == report.api_key).first()
    if not server:
        logger.warning(f"Rejected agent report: unrecognized or expired API key '{report.api_key[:12]}...'")
        raise HTTPException(status_code=401, detail="Invalid agent API key")

    now = datetime.utcnow()

    # Update server with REAL agent metrics
    if report.cpu_usage is not None:
        server.cpu_usage = report.cpu_usage
    if report.memory_usage is not None:
        server.memory_usage = report.memory_usage
    if report.disk_usage is not None:
        server.disk_usage = report.disk_usage
    if report.load_avg_1 is not None:
        server.load_avg_1 = report.load_avg_1
    if report.load_avg_5 is not None:
        server.load_avg_5 = report.load_avg_5
    if report.load_avg_15 is not None:
        server.load_avg_15 = report.load_avg_15
    if report.uptime_days is not None:
        server.uptime_days = report.uptime_days
    if report.error_count is not None:
        server.error_count = report.error_count
    if report.ram_total_gb is not None:
        server.ram_total_gb = report.ram_total_gb
    if report.swap_usage is not None:
        server.swap_usage = report.swap_usage
    if report.cpu_cores is not None:
        server.cpu_cores = report.cpu_cores
    if report.cpu_model is not None:
        server.cpu_model = report.cpu_model
    if report.hostname is not None:
        server.hostname = report.hostname
    if report.os_name is not None:
        server.os_name = report.os_name
    if report.os_version is not None:
        server.os_version = report.os_version
    if report.kernel is not None:
        server.kernel = report.kernel
    if report.architecture is not None:
        server.architecture = report.architecture
    if report.open_ports is not None:
        server.open_ports = report.open_ports
    if report.running_services is not None:
        server.running_services = report.running_services

    server.data_source = "agent"
    server.agent_last_seen = now
    server.agent_installed = True
    server.status = "active"
    server.last_scanned_at = now
    server.scan_status = "success"
    server.scan_error = None
    server.risk_score = calculate_server_risk(server)

    # Store health snapshots for time-series
    metrics_to_record = {
        "cpu_usage": report.cpu_usage,
        "memory_usage": report.memory_usage,
        "disk_usage": report.disk_usage,
        "loadavg": report.load_avg_1,
    }
    for metric_name, value in metrics_to_record.items():
        if value is not None:
            snapshot = HealthSnapshot(
                server_id=server.id,
                metric=metric_name,
                value=str(value),
                recorded_at=now,
            )
            db.add(snapshot)

    # Process local projects discovered by agent
    if report.discovered_projects:
        from services.server_scanner import upsert_discovery
        for proj in report.discovered_projects:
            if isinstance(proj, dict) and proj.get("name"):
                proj_data = {
                    "name": proj.get("name"),
                    "domain": proj.get("domain") or proj.get("name"),
                    "path": proj.get("path") or "/var/www/html",
                    "owner": proj.get("owner") or "root",
                    "framework": proj.get("framework") or "php",
                    "language": proj.get("language") or "php",
                    "size_mb": proj.get("size_mb", 100),
                    "dns_points_here": True,
                    "web_config_active": True,
                    "has_ssl": True,
                    "ssl_expiry_days": 60,
                    "days_since_modified": 10,
                    "is_live": True,
                    "is_inactive": False,
                    "env_type": "live",
                    "risk_score": 15,
                    "data_source": "agent",
                }
                upsert_discovery(db, server.id, proj_data)

    # Check alert thresholds and dispatch notifications
    _check_threshold_alerts(db, server)

    try:
        db.commit()
    except Exception as e:
        logger.error(f"Agent report commit error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to process report")

    return {"status": "ok", "risk_score": server.risk_score}


def _check_threshold_alerts(db: Session, server: Server):
    """Check if any metric exceeds alert thresholds and create alerts."""
    checks = [
        ("disk_high", server.disk_usage, DISK_WARN_THRESHOLD, DISK_CRIT_THRESHOLD, "Disk usage"),
        ("cpu_high", server.cpu_usage, CPU_WARN_THRESHOLD, CPU_CRIT_THRESHOLD, "CPU usage"),
        ("memory_high", server.memory_usage, MEM_WARN_THRESHOLD, MEM_CRIT_THRESHOLD, "Memory usage"),
    ]

    for alert_type, value, warn_thresh, crit_thresh, label in checks:
        if value is None:
            continue

        if value >= crit_thresh:
            severity = "critical"
        elif value >= warn_thresh:
            severity = "warning"
        else:
            # Value is normal — auto-resolve open alerts
            open_alerts = db.query(Alert).filter(
                Alert.server_id == server.id,
                Alert.type == alert_type,
                Alert.is_resolved == False,
            ).all()
            for a in open_alerts:
                a.is_resolved = True
                a.resolved_at = datetime.utcnow()
            continue

        # Check if we already have an open alert
        existing = db.query(Alert).filter(
            Alert.server_id == server.id,
            Alert.type == alert_type,
            Alert.is_resolved == False,
        ).first()

        if not existing:
            create_and_dispatch_alert(
                db,
                alert_type=alert_type,
                severity=severity,
                message=f"{label} on {server.name} is at {value}% ({severity}). Threshold: {warn_thresh}%",
                server_id=server.id,
                server_name=server.name,
            )


@router.post("/generate-key/{server_id}")
def generate_agent_key(
    server_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin"]))
):
    """Generate a new API key for a server's agent."""
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    api_key = f"infra_{secrets.token_hex(24)}"
    server.agent_api_key = api_key
    db.commit()

    return {"server_id": server_id, "api_key": api_key, "message": "Agent API key generated"}


def _resolve_base_url(request: Request) -> str:
    """Resolve the external reachable base URL, respecting reverse proxy headers and env overrides."""
    env_url = os.getenv("PUBLIC_API_URL") or os.getenv("APP_URL")
    if env_url:
        return env_url.rstrip("/")
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    if host:
        return f"{proto}://{host}".rstrip("/")
    return str(request.base_url).rstrip("/")


@router.get("/setup-command/{server_id}")
def get_agent_setup_command(
    server_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get or generate agent API key and 1-line installation command for a server."""
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    if not server.agent_api_key:
        server.agent_api_key = f"infra_{secrets.token_hex(24)}"
        db.commit()

    base_url = _resolve_base_url(request)
    install_command = f"curl -sSL {base_url}/agent/install.sh | bash -s -- --api-key={server.agent_api_key}"

    return {
        "server_id": server.id,
        "server_name": server.name,
        "api_key": server.agent_api_key,
        "install_command": install_command,
        "agent_installed": bool(server.agent_installed),
        "agent_last_seen": server.agent_last_seen.isoformat() if server.agent_last_seen else None,
        "status": server.status,
    }


@router.get("/install.sh")
def get_install_script(request: Request):
    """Serve the agent installation script."""
    base_url = _resolve_base_url(request)

    script = f"""#!/bin/bash
# AI Infrastructure Intelligence Platform — Agent Installer
# Usage: curl -sSL {base_url}/agent/install.sh | bash -s -- --api-key=YOUR_KEY

set -e

AGENT_DIR="/opt/infra-agent"
API_URL="{base_url}"
API_KEY=""

# Parse args
for arg in "$@"; do
    case $arg in
        --api-key=*) API_KEY="${{arg#*=}}" ;;
        --url=*) API_URL="${{arg#*=}}" ;;
    esac
done

if [ -z "$API_KEY" ]; then
    echo "ERROR: --api-key is required"
    echo "Usage: curl -sSL {base_url}/agent/install.sh | bash -s -- --api-key=YOUR_KEY"
    exit 1
fi

echo "🚀 Installing Infra Intel Agent..."
echo "   API URL: $API_URL"
echo "   Agent Dir: $AGENT_DIR"

mkdir -p $AGENT_DIR

cat > $AGENT_DIR/infra_agent.py << 'AGENT_EOF'
#!/usr/bin/env python3
\"\"\"
Infra Intel Agent — Lightweight server monitoring agent.
Reports real system metrics every 60 seconds via HTTPS POST.
Zero external dependencies — uses only Python stdlib.
\"\"\"
import json
import os
import re
import ssl
import subprocess
import sys
import time
import urllib.request
import urllib.error

CONFIG_FILE = "/opt/infra-agent/agent.conf"

def load_config():
    with open(CONFIG_FILE) as f:
        return json.load(f)

def get_cpu_usage():
    try:
        out = subprocess.check_output(["top", "-bn1"], timeout=5, stderr=subprocess.DEVNULL).decode()
        for line in out.splitlines():
            if "Cpu" in line or "%Cpu" in line:
                parts = re.findall(r"[\\d.]+", line)
                if len(parts) >= 4:
                    idle = float(parts[3])
                    return max(0, min(100, int(100 - idle)))
    except Exception:
        pass
    try:
        with open("/proc/stat") as f:
            line = f.readline()
        vals = list(map(int, line.split()[1:]))
        idle = vals[3]
        total = sum(vals)
        time.sleep(0.5)
        with open("/proc/stat") as f:
            line = f.readline()
        vals2 = list(map(int, line.split()[1:]))
        idle2 = vals2[3]
        total2 = sum(vals2)
        diff_idle = idle2 - idle
        diff_total = total2 - total
        if diff_total > 0:
            return max(0, min(100, int((1 - diff_idle / diff_total) * 100)))
    except Exception:
        pass
    return 0

def get_memory_usage():
    try:
        with open("/proc/meminfo") as f:
            info = {{}}
            for line in f:
                parts = line.split(":")
                if len(parts) == 2:
                    key = parts[0].strip()
                    val = int(re.findall(r"\\d+", parts[1])[0])
                    info[key] = val
            total = info.get("MemTotal", 1)
            available = info.get("MemAvailable", info.get("MemFree", 0))
            used_pct = int((1 - available / total) * 100)
            return max(0, min(100, used_pct)), round(total / 1048576, 1)
    except Exception:
        return 0, 0

def get_disk_usage():
    try:
        out = subprocess.check_output(["df", "-h", "/"], timeout=5).decode()
        for line in out.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 5:
                pct = parts[4].replace("%", "")
                return int(pct)
    except Exception:
        return 0

def get_load_avg():
    try:
        with open("/proc/loadavg") as f:
            parts = f.read().split()
            return float(parts[0]), float(parts[1]), float(parts[2])
    except Exception:
        return 0.0, 0.0, 0.0

def get_uptime_days():
    try:
        with open("/proc/uptime") as f:
            secs = float(f.read().split()[0])
            return int(secs / 86400)
    except Exception:
        return 0

def get_error_count():
    try:
        out = subprocess.check_output(
            ["journalctl", "--since", "24 hours ago", "-p", "err", "--no-pager", "-q"],
            timeout=10, stderr=subprocess.DEVNULL
        ).decode()
        return len(out.strip().splitlines())
    except Exception:
        return 0

def get_system_info():
    info = {{}}
    try:
        info["hostname"] = subprocess.check_output(["hostname"], timeout=3).decode().strip()
    except Exception:
        pass
    try:
        info["kernel"] = subprocess.check_output(["uname", "-r"], timeout=3).decode().strip()
    except Exception:
        pass
    try:
        info["architecture"] = subprocess.check_output(["uname", "-m"], timeout=3).decode().strip()
    except Exception:
        pass
    try:
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    info["os_name"] = line.split("=", 1)[1].strip().strip('"')
    except Exception:
        pass
    try:
        info["cpu_cores"] = int(subprocess.check_output(["nproc"], timeout=3).decode().strip())
    except Exception:
        pass
    try:
        out = subprocess.check_output(["lscpu"], timeout=5).decode()
        for line in out.splitlines():
            if "Model name" in line:
                info["cpu_model"] = line.split(":", 1)[1].strip()
                break
    except Exception:
        pass
    return info

def get_swap_usage():
    try:
        with open("/proc/meminfo") as f:
            info = {{}}
            for line in f:
                parts = line.split(":")
                if len(parts) == 2:
                    key = parts[0].strip()
                    val = int(re.findall(r"\\d+", parts[1])[0])
                    info[key] = val
            total = info.get("SwapTotal", 0)
            free = info.get("SwapFree", 0)
            if total > 0:
                return int((1 - free / total) * 100)
    except Exception:
        pass
    return 0

def send_report(config, data):
    url = config["api_url"].rstrip("/") + "/agent/report"
    payload = json.dumps(data).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={{"Content-Type": "application/json", "User-Agent": "InfraIntelAgent/1.0"}},
        method="POST",
    )
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {{e.code}} — {{e.read().decode()[:200]}}")
        return e.code
    except Exception as e:
        print(f"Send error: {{e}}")
        return None

def discover_local_projects():
    projs = []
    seen = set()
    userdomain_map = {{}}
    if os.path.exists("/etc/userdomains"):
        try:
            with open("/etc/userdomains") as f:
                for line in f:
                    if ":" in line:
                        dom, usr = line.split(":", 1)
                        userdomain_map[usr.strip()] = dom.strip()
        except Exception:
            pass

    if os.path.exists("/var/www/html"):
        try:
            if os.listdir("/var/www/html"):
                hostname = "web-app"
                try:
                    hostname = subprocess.check_output(["hostname"], timeout=2).decode().strip()
                except Exception:
                    pass
                dom = hostname if "." in hostname else hostname + ".local"
                seen.add("/var/www/html")
                projs.append({{"name": dom, "domain": dom, "path": "/var/www/html", "owner": "www-data", "framework": "php"}})
        except Exception:
            pass

    if os.path.exists("/home"):
        try:
            for u in os.listdir("/home"):
                html_path = os.path.join("/home", u, "public_html")
                if os.path.isdir(html_path):
                    dom = userdomain_map.get(u, u)
                    if dom not in seen:
                        seen.add(dom)
                        projs.append({{"name": dom, "domain": dom, "path": html_path, "owner": u, "framework": "php"}})
        except Exception:
            pass

    if os.path.exists("/var/www"):
        try:
            for d in os.listdir("/var/www"):
                wpath = os.path.join("/var/www", d)
                if os.path.isdir(wpath) and d not in ("html", "cgi-bin") and wpath not in seen:
                    seen.add(wpath)
                    projs.append({{"name": d, "domain": d, "path": wpath, "owner": "www-data", "framework": "php"}})
        except Exception:
            pass
    return projs

def main():
    config = load_config()
    print(f"Infra Intel Agent started. Reporting to {{config['api_url']}} every 60s")

    while True:
        try:
            mem_pct, ram_gb = get_memory_usage()
            l1, l5, l15 = get_load_avg()
            sys_info = get_system_info()

            report = {{
                "api_key": config["api_key"],
                "cpu_usage": get_cpu_usage(),
                "memory_usage": mem_pct,
                "disk_usage": get_disk_usage(),
                "load_avg_1": l1,
                "load_avg_5": l5,
                "load_avg_15": l15,
                "uptime_days": get_uptime_days(),
                "error_count": get_error_count(),
                "ram_total_gb": ram_gb,
                "swap_usage": get_swap_usage(),
                "discovered_projects": discover_local_projects(),
                **sys_info,
            }}

            status = send_report(config, report)
            if status == 200:
                print(f"[{{time.strftime('%H:%M:%S')}}] Report sent — CPU:{{report['cpu_usage']}}% MEM:{{report['memory_usage']}}% DISK:{{report['disk_usage']}}%")
            else:
                print(f"[{{time.strftime('%H:%M:%S')}}] Report failed — status={{status}}")

        except Exception as e:
            print(f"Agent error: {{e}}")

        time.sleep(60)

if __name__ == "__main__":
    main()
AGENT_EOF

# Write config
cat > $AGENT_DIR/agent.conf << EOF
{{
    "api_key": "$API_KEY",
    "api_url": "$API_URL"
}}
EOF

chmod +x $AGENT_DIR/infra_agent.py

# Create systemd service
cat > /etc/systemd/system/infra-agent.service << EOF
[Unit]
Description=Infra Intel Monitoring Agent
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 $AGENT_DIR/infra_agent.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable infra-agent
systemctl start infra-agent

echo ""
echo "✅ Infra Intel Agent installed and running!"
echo "   Service: systemctl status infra-agent"
echo "   Logs: journalctl -u infra-agent -f"
echo "   Config: $AGENT_DIR/agent.conf"
"""
    return PlainTextResponse(content=script, media_type="text/plain")


@router.get("/status")
def get_agent_status(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get agent installation status for all servers."""
    servers = db.query(Server).all()
    return [
        {
            "server_id": s.id,
            "server_name": s.name,
            "agent_installed": s.agent_installed or False,
            "agent_last_seen": s.agent_last_seen.isoformat() if s.agent_last_seen else None,
            "data_source": s.data_source,
            "has_api_key": bool(s.agent_api_key),
        }
        for s in servers
    ]
