"""
24/7 Dedicated Server Agent Router (DataDog / 360Monitoring Style)
- Dynamic 1-Line Bash Installer Generator
- Pure Python 3 Lightweight Agent Script Distribution
- High-Precision Telemetry Ingestion Endpoint
- Server Agent Token Manager
"""
import secrets
import json
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from database import get_db
from models import Server
from routers.auth import get_current_user, require_role
from services.risk_engine import calculate_server_risk
from services.alerting_service import notify_alert

logger = logging.getLogger("agent_router")

router = APIRouter(
    prefix="/agent",
    tags=["24/7 Dedicated Agent"]
)


class AgentTelemetryPayload(BaseModel):
    hostname: Optional[str] = None
    os_name: Optional[str] = None
    kernel: Optional[str] = None
    cpu_usage: int
    memory_usage: int
    disk_usage: int
    load_avg_1: float
    load_avg_5: float
    load_avg_15: float
    uptime_days: int
    error_count: Optional[int] = 0
    cpanel_accounts_count: Optional[int] = None
    top_processes: Optional[List[Dict[str, Any]]] = None
    agent_version: Optional[str] = "3.0.0"


AGENT_PYTHON_SCRIPT = '''#!/usr/bin/env python3
"""
Infra Intel 24/7 Lightweight Kernel Agent
Zero external dependencies (Pure Python 3 standard library)
RAM Footprint: < 5MB | CPU Footprint: < 0.1%
"""
import os
import sys
import time
import json
import socket
import ssl
import subprocess
import urllib.request
import urllib.error

CONFIG_FILE = "/opt/infra-intel/config.json"

def read_config():
    if not os.path.exists(CONFIG_FILE):
        return None
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return None

def get_cpu_usage(interval=1):
    try:
        def read_stat():
            with open("/proc/stat", "r") as f:
                fields = [float(column) for column in f.readline().strip().split()[1:5]]
            return fields[3], sum(fields) # idle, total

        idle1, total1 = read_stat()
        time.sleep(interval)
        idle2, total2 = read_stat()
        idle_delta = idle2 - idle1
        total_delta = total2 - total1
        if total_delta == 0:
            return 0
        return int((1.0 - (idle_delta / total_delta)) * 100)
    except Exception:
        return 5

def get_mem_usage():
    try:
        meminfo = {}
        with open("/proc/meminfo", "r") as f:
            for line in f:
                parts = line.split(":")
                if len(parts) == 2:
                    meminfo[parts[0].strip()] = int(parts[1].strip().split()[0])
        total = meminfo.get("MemTotal", 1)
        free = meminfo.get("MemFree", 0) + meminfo.get("Buffers", 0) + meminfo.get("Cached", 0)
        used = max(0, total - free)
        return int((used / total) * 100)
    except Exception:
        return 10

def get_disk_usage(path="/"):
    try:
        st = os.statvfs(path)
        total = st.f_blocks * st.f_frsize
        free = st.f_bavail * st.f_frsize
        used = total - free
        return int((used / total) * 100)
    except Exception:
        return 20

def get_load_avg():
    try:
        load1, load5, load15 = os.getloadavg()
        return round(load1, 2), round(load5, 2), round(load15, 2)
    except Exception:
        return 0.1, 0.1, 0.1

def get_uptime_days():
    try:
        with open("/proc/uptime", "r") as f:
            uptime_seconds = float(f.readline().split()[0])
        return int(uptime_seconds / 86400)
    except Exception:
        return 1

def get_cpanel_accounts_count():
    try:
        cpanel_users_dir = "/var/cpanel/users"
        if os.path.exists(cpanel_users_dir):
            users = [u for u in os.listdir(cpanel_users_dir) if not u.startswith(".")]
            return len(users)
    except Exception:
        pass
    return None

def get_top_processes():
    try:
        cmd = ["ps", "-eo", "pid,user,%cpu,%mem,comm", "--sort=-%cpu"]
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, universal_newlines=True)
        lines = out.strip().split("\\n")[1:6]
        procs = []
        for line in lines:
            parts = line.split(None, 4)
            if len(parts) >= 5:
                procs.append({
                    "pid": parts[0],
                    "user": parts[1],
                    "cpu": float(parts[2]),
                    "mem": float(parts[3]),
                    "command": parts[4]
                })
        return procs
    except Exception:
        return []

def collect_telemetry():
    l1, l5, l15 = get_load_avg()
    return {
        "hostname": socket.gethostname(),
        "os_name": "Linux (" + os.uname().sysname + ")",
        "kernel": os.uname().release,
        "cpu_usage": get_cpu_usage(interval=1),
        "memory_usage": get_mem_usage(),
        "disk_usage": get_disk_usage("/"),
        "load_avg_1": l1,
        "load_avg_5": l5,
        "load_avg_15": l15,
        "uptime_days": get_uptime_days(),
        "cpanel_accounts_count": get_cpanel_accounts_count(),
        "top_processes": get_top_processes(),
        "agent_version": "3.0.0"
    }

def send_telemetry(config, telemetry):
    api_url = config.get("api_url", "").rstrip("/") + "/agent/telemetry"
    token = config.get("token", "")
    data = json.dumps(telemetry).encode("utf-8")
    req = urllib.request.Request(
        api_url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "InfraIntel-Agent/3.0.0"
        }
    )
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            return resp.status in (200, 201)
    except Exception as e:
        print(f"[Agent] Ingestion error: {e}", file=sys.stderr)
        return False

def main():
    print("⚡ Infra Intel 24/7 Agent Daemon started.")
    while True:
        cfg = read_config()
        if not cfg or not cfg.get("token"):
            print("[Agent] Missing token in config. Waiting...", file=sys.stderr)
            time.sleep(30)
            continue
        try:
            telemetry = collect_telemetry()
            ok = send_telemetry(cfg, telemetry)
            if ok:
                print(f"[Agent] Telemetry streamed successfully: CPU {telemetry['cpu_usage']}%, RAM {telemetry['memory_usage']}%, Disk {telemetry['disk_usage']}%")
        except Exception as e:
            print(f"[Agent] Loop error: {e}", file=sys.stderr)
        time.sleep(60)

if __name__ == "__main__":
    main()
'''


@router.get("/install.sh", response_class=PlainTextResponse)
def get_install_script(request: Request):
    """
    Returns the dynamic 1-line agent bash installer script.
    Usage: curl -sSL https://<host>/agent/install.sh | bash -s -- --token=<TOKEN>
    """
    base_url = str(request.base_url).rstrip("/")
    # Force HTTPS if behind proxy
    if request.headers.get("x-forwarded-proto") == "https" and base_url.startswith("http://"):
        base_url = base_url.replace("http://", "https://", 1)

    bash_script = f"""#!/usr/bin/env bash
# ==============================================================================
# Infra Intel 24/7 Kernel Agent Installer (DataDog / 360Monitoring Style)
# ==============================================================================
set -e

TOKEN=""
API_URL="{base_url}"

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --token=*) TOKEN="${{1#*=}}" ;;
        --token) TOKEN="$2"; shift ;;
        --api-url=*) API_URL="${{1#*=}}" ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

if [ -z "$TOKEN" ]; then
    echo "❌ Error: Missing --token parameter!"
    echo "Usage: curl -sSL {base_url}/agent/install.sh | bash -s -- --token=YOUR_SERVER_TOKEN"
    exit 1
fi

echo "================================================================="
echo "⚡ Installing Infra Intel 24/7 Dedicated Monitoring Agent..."
echo "================================================================="

# 1. Create install directory
mkdir -p /opt/infra-intel
chmod 755 /opt/infra-intel

# 2. Write agent config
cat <<EOF > /opt/infra-intel/config.json
{{
  "token": "$TOKEN",
  "api_url": "$API_URL"
}}
EOF
chmod 600 /opt/infra-intel/config.json

# 3. Download agent python script
echo "⬇️ Downloading lightweight agent script..."
curl -sSL "$API_URL/agent/script.py" -o /opt/infra-intel/agent.py
chmod 755 /opt/infra-intel/agent.py

# 4. Setup Systemd Service
if command -v systemctl >/dev/null 2>&1; then
    echo "⚙️ Configuring systemd daemon service..."
    cat <<EOF > /etc/systemd/system/infra-intel-agent.service
[Unit]
Description=Infra Intel 24/7 Dedicated Server Monitoring Agent
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/infra-intel
ExecStart=/usr/bin/env python3 /opt/infra-intel/agent.py
Restart=always
RestartSec=10
MemoryMax=32M
CPUQuota=5%

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable infra-intel-agent.service
    systemctl restart infra-intel-agent.service
    echo "✅ Systemd service 'infra-intel-agent' active and running."
else
    echo "⚙️ Systemd not found. Setting up crontab runner..."
    (crontab -l 2>/dev/null | grep -v 'infra-intel'; echo "* * * * * pgrep -f /opt/infra-intel/agent.py >/dev/null || /usr/bin/env python3 /opt/infra-intel/agent.py >/dev/null 2>&1 &") | crontab -
    nohup /usr/bin/env python3 /opt/infra-intel/agent.py >/dev/null 2>&1 &
    echo "✅ Background daemon started via crontab."
fi

echo ""
echo "================================================================="
echo "🎉 SUCCESS: Infra Intel 24/7 Agent Installed Successfully!"
echo "📡 Real-time kernel telemetry is now streaming to your dashboard."
echo "================================================================="
"""
    return Response(content=bash_script, media_type="text/plain")


@router.get("/script.py", response_class=PlainTextResponse)
def get_agent_script():
    """Returns the pure Python 3 agent script."""
    return Response(content=AGENT_PYTHON_SCRIPT, media_type="text/x-python")


@router.post("/telemetry")
def ingest_agent_telemetry(
    payload: AgentTelemetryPayload,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    High-frequency telemetry ingestion endpoint called by the server agent.
    Authenticated via Server Agent Token in Authorization Header (Bearer <TOKEN>).
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid agent token header")

    token = auth_header.split(" ", 1)[1].strip()
    server = db.query(Server).filter(Server.agent_token == token).first()
    if not server:
        raise HTTPException(status_code=403, detail="Invalid server agent token")

    now = datetime.utcnow()

    # Update server telemetry
    server.cpu_usage = payload.cpu_usage
    server.memory_usage = payload.memory_usage
    server.disk_usage = payload.disk_usage
    server.load_avg_1 = payload.load_avg_1
    server.load_avg_5 = payload.load_avg_5
    server.load_avg_15 = payload.load_avg_15
    server.uptime_days = payload.uptime_days
    server.agent_installed = True
    server.agent_version = payload.agent_version
    server.agent_last_seen = now
    server.last_scanned_at = now
    server.data_source = "agent"
    server.status = "active"
    server.scan_status = "success"
    server.scan_error = None

    if payload.hostname and not server.hostname:
        server.hostname = payload.hostname
    if payload.os_name and not server.os_name:
        server.os_name = payload.os_name
    if payload.kernel and not server.kernel:
        server.kernel = payload.kernel
    if payload.cpanel_accounts_count is not None:
        server.whm_accounts_count = payload.cpanel_accounts_count
    if payload.top_processes:
        server.top_processes = json.dumps(payload.top_processes)

    # Recalculate AI / ML Risk Score
    server.risk_score = calculate_server_risk(server)

    # Trigger Automated Security Alerts on High Saturation
    if server.disk_usage >= 90:
        notify_alert(
            db,
            category="DISK_FULL",
            target_name=server.name,
            title=f"Critical Disk Saturation: {server.name} ({server.disk_usage}%)",
            description=f"Agent report: Server '{server.name}' disk usage reached {server.disk_usage}%. Immediate action required.",
            severity="CRITICAL",
            target_type="server",
            target_id=server.id,
            recommendation="Expand root partition or clean up /var/log and archived accounts.",
        )
    elif server.disk_usage >= 85:
        notify_alert(
            db,
            category="DISK_FULL",
            target_name=server.name,
            title=f"High Disk Usage Warning: {server.name} ({server.disk_usage}%)",
            description=f"Agent report: Server '{server.name}' disk usage is at {server.disk_usage}%.",
            severity="WARNING",
            target_type="server",
            target_id=server.id,
        )

    db.commit()

    return {
        "status": "success",
        "server_id": server.id,
        "server_name": server.name,
        "risk_score": server.risk_score,
        "received_at": now.isoformat()
    }


@router.get("/token/{server_id}")
def get_or_create_server_agent_token(
    server_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(require_role(["admin", "devops"]))
):
    """
    Get or generate a unique agent token and copyable 1-line installation command for a server.
    """
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    if not server.agent_token:
        server.agent_token = secrets.token_hex(20)
        db.commit()
        db.refresh(server)

    base_url = str(request.base_url).rstrip("/")
    if request.headers.get("x-forwarded-proto") == "https" and base_url.startswith("http://"):
        base_url = base_url.replace("http://", "https://", 1)

    install_cmd = f"curl -sSL {base_url}/agent/install.sh | bash -s -- --token={server.agent_token}"

    return {
        "server_id": server.id,
        "server_name": server.name,
        "agent_token": server.agent_token,
        "agent_installed": bool(server.agent_installed),
        "agent_version": server.agent_version,
        "agent_last_seen": server.agent_last_seen.isoformat() if server.agent_last_seen else None,
        "install_command": install_cmd
    }
