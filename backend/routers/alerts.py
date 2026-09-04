"""
Alerts Router — Unified Alert Management API
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Alert, MalwareAlert, Server
from routers.auth import get_current_user, require_role

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("/")
def get_alerts(
    alert_type: Optional[str] = None,
    severity: Optional[str] = None,
    server_id: Optional[int] = None,
    resolved: Optional[bool] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """List all alerts with filtering and pagination."""
    query = db.query(Alert)

    if alert_type:
        query = query.filter(Alert.type == alert_type)
    if severity:
        query = query.filter(Alert.severity == severity)
    if server_id:
        query = query.filter(Alert.server_id == server_id)
    if resolved is not None:
        query = query.filter(Alert.is_resolved == resolved)

    total = query.count()
    total_open = db.query(Alert).filter(Alert.is_resolved == False).count()
    alerts = query.order_by(Alert.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

    return {
        "total": total,
        "total_open": total_open,
        "page": page,
        "limit": limit,
        "alerts": [
            {
                "id": a.id,
                "server_id": a.server_id,
                "server_name": a.server.name if a.server else None,
                "site_id": a.site_id,
                "site_domain": a.site.domain if a.site else None,
                "type": a.type,
                "severity": a.severity,
                "message": a.message,
                "is_resolved": a.is_resolved,
                "notification_sent": a.notification_sent,
                "teams_sent_at": a.teams_sent_at.isoformat() if a.teams_sent_at else None,
                "email_sent_at": a.email_sent_at.isoformat() if a.email_sent_at else None,
                "whatsapp_sent_at": a.whatsapp_sent_at.isoformat() if a.whatsapp_sent_at else None,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
            }
            for a in alerts
        ]
    }


@router.post("/{alert_id}/resolve")
def resolve_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin", "devops"]))
):
    """Resolve an alert."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.is_resolved = True
    alert.resolved_at = datetime.utcnow()
    db.commit()

    return {"message": f"Alert #{alert_id} resolved", "alert_id": alert_id}


@router.post("/{alert_id}/acknowledge")
def acknowledge_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin", "devops"]))
):
    """Acknowledge an alert (marks notification as sent without resolving)."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.notification_sent = True
    db.commit()

    return {"message": f"Alert #{alert_id} acknowledged", "alert_id": alert_id}


@router.get("/malware")
def get_malware_alerts(
    server_id: Optional[int] = None,
    resolved: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get malware scan findings."""
    query = db.query(MalwareAlert)

    if server_id:
        query = query.filter(MalwareAlert.server_id == server_id)
    if resolved is not None:
        query = query.filter(MalwareAlert.is_resolved == resolved)

    alerts = query.order_by(MalwareAlert.detected_at.desc()).limit(100).all()

    return [
        {
            "id": a.id,
            "server_id": a.server_id,
            "server_name": a.server.name if a.server else None,
            "file_path": a.file_path,
            "threat_type": a.threat_type,
            "severity": a.severity,
            "details": a.details,
            "is_resolved": a.is_resolved,
            "detected_at": a.detected_at.isoformat() if a.detected_at else None,
            "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
        }
        for a in alerts
    ]


@router.post("/malware/{alert_id}/resolve")
def resolve_malware_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin", "devops"]))
):
    """Resolve a malware alert."""
    alert = db.query(MalwareAlert).filter(MalwareAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Malware alert not found")

    alert.is_resolved = True
    alert.resolved_at = datetime.utcnow()
    db.commit()

    return {"message": f"Malware alert #{alert_id} resolved"}


@router.post("/scan-malware/{server_id}")
def trigger_malware_scan(
    server_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin", "devops"]))
):
    """Trigger an on-demand malware scan for a specific server."""
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    from services.malware_scanner import scan_server_malware
    result = scan_server_malware(db, server)

    return result


class AlertConfigSchema(BaseModel):
    teams_webhook_url: Optional[str] = None
    email_to: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    # WhatsApp User & Group notification settings
    whatsapp_enabled: Optional[bool] = True
    whatsapp_user_phone: Optional[str] = None
    whatsapp_group_id: Optional[str] = None
    whatsapp_provider: Optional[str] = "callmebot"
    whatsapp_api_key: Optional[str] = None
    whatsapp_api_url: Optional[str] = None


@router.get("/config")
def get_alert_config(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get current notification settings."""
    from services.notification_service import _get_teams_webhook_url, _get_smtp_config, _get_whatsapp_config
    cfg = db.query(AlertConfig).first()
    env_webhook = _get_teams_webhook_url(db)
    env_smtp = _get_smtp_config(db)
    env_wa = _get_whatsapp_config(db)

    return {
        "teams_webhook_url": cfg.teams_webhook_url if (cfg and cfg.teams_webhook_url) else env_webhook or "",
        "email_to": cfg.email_to if (cfg and cfg.email_to) else env_smtp.get("to", ""),
        "smtp_host": cfg.smtp_host if (cfg and cfg.smtp_host) else env_smtp.get("host", ""),
        "smtp_port": cfg.smtp_port if (cfg and cfg.smtp_port) else env_smtp.get("port", 587),
        "smtp_user": cfg.smtp_user if (cfg and cfg.smtp_user) else env_smtp.get("user", ""),
        "smtp_password": cfg.smtp_password if (cfg and cfg.smtp_password) else env_smtp.get("password", ""),
        "teams_configured": bool(env_webhook),
        "email_configured": bool(env_smtp.get("host") and env_smtp.get("user") and env_smtp.get("to")),
        # WhatsApp User & Group configurations
        "whatsapp_enabled": cfg.whatsapp_enabled if (cfg and cfg.whatsapp_enabled is not None) else env_wa.get("enabled", True),
        "whatsapp_user_phone": cfg.whatsapp_user_phone if (cfg and cfg.whatsapp_user_phone) else env_wa.get("user_phone", ""),
        "whatsapp_group_id": cfg.whatsapp_group_id if (cfg and cfg.whatsapp_group_id) else env_wa.get("group_id", ""),
        "whatsapp_provider": cfg.whatsapp_provider if (cfg and cfg.whatsapp_provider) else env_wa.get("provider", "callmebot"),
        "whatsapp_api_key": cfg.whatsapp_api_key if (cfg and cfg.whatsapp_api_key) else env_wa.get("api_key", ""),
        "whatsapp_api_url": cfg.whatsapp_api_url if (cfg and cfg.whatsapp_api_url) else env_wa.get("api_url", ""),
        "whatsapp_configured": bool((env_wa.get("user_phone") or env_wa.get("group_id")) and env_wa.get("enabled")),
    }


@router.post("/config")
def save_alert_config(
    payload: AlertConfigSchema,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin", "devops"]))
):
    """Save or update notification settings."""
    cfg = db.query(AlertConfig).first()
    if not cfg:
        cfg = AlertConfig()
        db.add(cfg)

    if payload.teams_webhook_url is not None: cfg.teams_webhook_url = payload.teams_webhook_url.strip()
    if payload.email_to is not None: cfg.email_to = payload.email_to.strip()
    if payload.smtp_host is not None: cfg.smtp_host = payload.smtp_host.strip()
    if payload.smtp_port is not None: cfg.smtp_port = payload.smtp_port
    if payload.smtp_user is not None: cfg.smtp_user = payload.smtp_user.strip()
    if payload.smtp_password is not None: cfg.smtp_password = payload.smtp_password.strip()

    # WhatsApp settings
    if payload.whatsapp_enabled is not None: cfg.whatsapp_enabled = payload.whatsapp_enabled
    if payload.whatsapp_user_phone is not None: cfg.whatsapp_user_phone = payload.whatsapp_user_phone.strip()
    if payload.whatsapp_group_id is not None: cfg.whatsapp_group_id = payload.whatsapp_group_id.strip()
    if payload.whatsapp_provider is not None: cfg.whatsapp_provider = payload.whatsapp_provider.strip()
    if payload.whatsapp_api_key is not None: cfg.whatsapp_api_key = payload.whatsapp_api_key.strip()
    if payload.whatsapp_api_url is not None: cfg.whatsapp_api_url = payload.whatsapp_api_url.strip()

    db.commit()
    return {"message": "Notification configuration saved successfully!"}


@router.post("/test-whatsapp-user")
def test_whatsapp_user(
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin", "devops"]))
):
    """Send an instant test alert to configured WhatsApp user."""
    from services.notification_service import send_whatsapp_alert, _get_whatsapp_config
    wa_cfg = _get_whatsapp_config(db)
    if not wa_cfg.get("user_phone"):
        raise HTTPException(status_code=400, detail="WhatsApp User Phone Number is not configured.")

    dummy_alert = Alert(
        server_id=None,
        type="whatsapp_test",
        severity="info",
        message="🚀 Test notification from AI Infrastructure Intelligence Platform. Your WhatsApp user alert channel is live!",
        created_at=datetime.utcnow()
    )
    res = send_whatsapp_alert(dummy_alert, server_name="Production Control Center", target="user", db=db)
    if not res.get("user_sent"):
        detail = "; ".join(res.get("errors", [])) or "Failed to deliver WhatsApp test message. Please verify your phone number and API key."
        raise HTTPException(status_code=500, detail=detail)

    return {"message": "✅ Test alert delivered successfully to WhatsApp User!"}


@router.post("/test-whatsapp-group")
def test_whatsapp_group(
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin", "devops"]))
):
    """Send an instant test alert to configured WhatsApp group."""
    from services.notification_service import send_whatsapp_alert, _get_whatsapp_config
    wa_cfg = _get_whatsapp_config(db)
    if not wa_cfg.get("group_id"):
        raise HTTPException(status_code=400, detail="WhatsApp Group ID / Name is not configured.")

    dummy_alert = Alert(
        server_id=None,
        type="whatsapp_group_test",
        severity="info",
        message="👥 Test notification from AI Infrastructure Intelligence Platform. Your WhatsApp group alert channel is connected!",
        created_at=datetime.utcnow()
    )
    res = send_whatsapp_alert(dummy_alert, server_name="Production Control Center", target="group", db=db)
    if not res.get("group_sent"):
        detail = "; ".join(res.get("errors", [])) or "Failed to deliver WhatsApp test message to group. Please check Group ID and API key."
        raise HTTPException(status_code=500, detail=detail)

    return {"message": "✅ Test alert delivered successfully to WhatsApp Group!"}


@router.post("/test-teams")
def test_teams_webhook(
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin", "devops"]))
):
    """Send an instant test alert card to the configured Microsoft Teams / Slack webhook."""
    from services.notification_service import send_teams_alert, _get_teams_webhook_url
    webhook_url = _get_teams_webhook_url(db)
    if not webhook_url:
        raise HTTPException(status_code=400, detail="Microsoft Teams Webhook URL is not configured.")

    dummy_alert = Alert(
        server_id=None,
        type="test_notification",
        severity="info",
        message="🚀 Test notification from AI Infrastructure Intelligence Platform. Your Teams webhook connection is working perfectly!",
        created_at=datetime.utcnow(),
    )
    ok = send_teams_alert(dummy_alert, server_name="Production Control Center", db=db)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to deliver test message to Teams webhook. Verify the URL.")

    return {"message": "✅ Test Teams webhook notification sent successfully!"}


@router.post("/test-email")
def test_email_alert(
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin", "devops"]))
):
    """Send an instant test alert email via SMTP."""
    from services.notification_service import send_email_alert, _get_smtp_config
    smtp_cfg = _get_smtp_config(db)
    if not all([smtp_cfg.get("host"), smtp_cfg.get("user"), smtp_cfg.get("to")]):
        raise HTTPException(status_code=400, detail="SMTP settings or recipient email is incomplete.")

    dummy_alert = Alert(
        server_id=None,
        type="test_notification",
        severity="info",
        message="📧 Test notification from AI Infrastructure Intelligence Platform. Your SMTP email configuration is active!",
        created_at=datetime.utcnow(),
    )
    ok = send_email_alert(dummy_alert, server_name="Production Control Center", db=db)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to send test email. Please check SMTP host, port, credentials and TLS settings.")

    return {"message": f"✅ Test alert email sent to {smtp_cfg.get('to')}!"}
