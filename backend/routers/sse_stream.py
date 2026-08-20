"""
Server-Sent Events (SSE) Live Streaming Router
Streams real-time event pulses, uptime status changes, and server resource metrics directly to frontend clients.
"""
import asyncio
import json
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
from models import Server, UptimeCheck, Alert

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/stream", tags=["Live Streaming"])


async def event_generator(request: Request, db_factory):
    """Asynchronous generator yielding Real-Time Server-Sent Events (SSE) every 3 seconds."""
    while True:
        if await request.is_disconnected():
            break

        try:
            db: Session = next(db_factory())
            try:
                # Fetch recent metrics summary
                servers = db.query(Server).all()
                total_servers = len(servers)
                high_cpu_servers = sum(1 for s in servers if (s.cpu_usage or 0) >= 85)

                recent_down = db.query(UptimeCheck).filter(
                    UptimeCheck.is_up == False,
                    UptimeCheck.checked_at >= datetime.utcnow() - asyncio.subprocess.timedelta(minutes=15)
                ).count() if hasattr(asyncio.subprocess, 'timedelta') else 0

                open_alerts = db.query(Alert).filter(Alert.is_resolved == False).count()

                payload = {
                    "event_type": "telemetry_pulse",
                    "timestamp": datetime.utcnow().isoformat(),
                    "total_servers": total_servers,
                    "high_cpu_servers": high_cpu_servers,
                    "open_alerts": open_alerts,
                    "servers": [
                        {
                            "id": s.id,
                            "name": s.name,
                            "ip": s.ip_address,
                            "cpu": s.cpu_usage or 0,
                            "ram": s.memory_usage or 0,
                            "disk": s.disk_usage or 0,
                            "status": s.status
                        } for s in servers
                    ]
                }
                yield f"data: {json.dumps(payload)}\n\n"
            finally:
                db.close()
        except Exception as e:
            logger.debug(f"SSE stream error: {e}")

        await asyncio.sleep(3)


@router.get("/events")
async def stream_live_events(request: Request):
    """SSE Streaming Endpoint for real-time live monitoring dashboard updates."""
    return StreamingResponse(
        event_generator(request, get_db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
