from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import time

import models
from database import get_db
from models import Server, ProjectDiscovery
from services.risk_engine import calculate_server_risk
from services.insights_engine import generate_server_insights

router = APIRouter(prefix="/stats", tags=["Stats"])

_cache = {"data": None, "ts": 0}
CACHE_TTL = 300

@router.get("/dashboard")
def dashboard_stats(db: Session = Depends(get_db)):
    global _cache
    now = time.time()
    if _cache["data"] and (now - _cache["ts"]) < CACHE_TTL:
        return _cache["data"]

    total_servers = db.query(models.Server).count()
    total_projects = db.query(ProjectDiscovery).count()
    servers = db.query(Server).all()

    for server in servers:
        server.risk_score = calculate_server_risk(server)
    db.commit()

    critical_servers = len([s for s in servers if s.risk_score >= 60])
    warning_servers = len([s for s in servers if 30 <= s.risk_score < 60])
    healthy_servers = len([s for s in servers if s.risk_score < 30])
    top_risk_servers = sorted(servers, key=lambda x: x.risk_score, reverse=True)[:5]

    result = {
        "total_servers": total_servers,
        "total_projects": total_projects,
        "healthy_servers": healthy_servers,
        "warning_servers": warning_servers,
        "critical_servers": critical_servers,
        "top_risk_servers": [
            {
                "id": s.id,
                "name": s.name,
                "ip_address": s.ip_address,
                "risk_score": s.risk_score,
                "status": s.status,
                "cpu_usage": s.cpu_usage,
                "memory_usage": s.memory_usage,
                "disk_usage": s.disk_usage,
                "uptime_days": s.uptime_days,
                "insights": generate_server_insights(s)
            }
            for s in top_risk_servers
        ]
    }
    _cache = {"data": result, "ts": now}
    return result
