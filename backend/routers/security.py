"""
Security & Malware Alerts API Router
- Active & Resolved security vulnerability alerts
- Security audit triggers
- Microsoft Teams & Email Alert Channel Settings
- Test Alert Dispatcher
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db
from routers.auth import get_current_user, require_role
from services.security_scanner import run_full_security_audit
from services.alerting_service import get_alert_config, send_teams_alert, send_email_alert
from models import SecurityAlert, AlertConfig

router = APIRouter(
    prefix="/security",
    tags=["Security & Alerts"]
)


class AlertConfigUpdate(BaseModel):
    teams_webhook_url: Optional[str] = None
    teams_enabled: Optional[bool] = None
    email_recipients: Optional[str] = None
    email_enabled: Optional[bool] = None
    alert_on_disk_full: Optional[bool] = True
    alert_on_website_down: Optional[bool] = True
    alert_on_malware: Optional[bool] = True


@router.get("/alerts")
def list_security_alerts(
    resolved: bool = False,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List security, malware, and disk threshold alerts."""
    query = db.query(SecurityAlert)
    if not resolved:
        query = query.filter(SecurityAlert.is_resolved == False)
    alerts = query.order_by(SecurityAlert.created_at.desc()).all()

    critical_count = db.query(SecurityAlert).filter(SecurityAlert.is_resolved == False, SecurityAlert.severity == "CRITICAL").count()
    warning_count = db.query(SecurityAlert).filter(SecurityAlert.is_resolved == False, SecurityAlert.severity == "WARNING").count()

    return {
        "total_active": len(alerts) if not resolved else db.query(SecurityAlert).filter(SecurityAlert.is_resolved == False).count(),
        "critical_count": critical_count,
        "warning_count": warning_count,
        "alerts": [
            {
                "id": a.id,
                "target_type": a.target_type,
                "target_id": a.target_id,
                "target_name": a.target_name,
                "severity": a.severity,
                "category": a.category,
                "title": a.title,
                "description": a.description,
                "recommendation": a.recommendation,
                "is_resolved": a.is_resolved,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
            }
            for a in alerts
        ]
    }


@router.post("/scan-now")
def trigger_security_scan(
    db: Session = Depends(get_db),
    current_user = Depends(require_role(["admin", "devops"]))
):
    """Run an on-demand comprehensive security and malware audit across servers and projects."""
    result = run_full_security_audit(db)
    return result


@router.post("/alerts/{alert_id}/resolve")
def resolve_security_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_role(["admin", "devops"]))
):
    """Mark a security alert as resolved."""
    alert = db.query(SecurityAlert).filter(SecurityAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.is_resolved = True
    alert.resolved_at = datetime.utcnow()
    db.commit()

    return {"message": "Alert marked as resolved", "alert_id": alert.id}


@router.get("/config")
def get_alert_settings(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Retrieve current Microsoft Teams & Email notification settings."""
    cfg = get_alert_config(db)
    return {
        "teams_webhook_url": cfg.teams_webhook_url if cfg else "",
        "teams_enabled": bool(cfg.teams_enabled) if cfg else False,
        "email_recipients": cfg.email_recipients if cfg else "",
        "email_enabled": bool(cfg.email_enabled) if cfg else False,
        "alert_on_disk_full": bool(cfg.alert_on_disk_full) if cfg else True,
        "alert_on_website_down": bool(cfg.alert_on_website_down) if cfg else True,
        "alert_on_malware": bool(cfg.alert_on_malware) if cfg else True,
    }


@router.post("/config")
def update_alert_settings(
    update: AlertConfigUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_role(["admin"]))
):
    """Update Microsoft Teams & Email notification settings."""
    cfg = get_alert_config(db)
    if not cfg:
        cfg = AlertConfig()
        db.add(cfg)

    if update.teams_webhook_url is not None:
        cfg.teams_webhook_url = update.teams_webhook_url
    if update.teams_enabled is not None:
        cfg.teams_enabled = update.teams_enabled
    if update.email_recipients is not None:
        cfg.email_recipients = update.email_recipients
    if update.email_enabled is not None:
        cfg.email_enabled = update.email_enabled
    if update.alert_on_disk_full is not None:
        cfg.alert_on_disk_full = update.alert_on_disk_full
    if update.alert_on_website_down is not None:
        cfg.alert_on_website_down = update.alert_on_website_down
    if update.alert_on_malware is not None:
        cfg.alert_on_malware = update.alert_on_malware

    cfg.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "Alert channel configuration saved successfully", "config": update.dict()}


@router.post("/test-alert")
def send_test_alert(
    channel: str = "both",  # teams, email, both
    db: Session = Depends(get_db),
    current_user = Depends(require_role(["admin", "devops"]))
):
    """Dispatch an immediate test alert to configured Microsoft Teams & Email channels."""
    cfg = get_alert_config(db)
    results = {}

    title = "Test Security Alert: 24/7 Monitoring Sentinel"
    desc = "This is a test notification from the AI Infrastructure Intelligence Platform confirming active integration with Microsoft Teams and Email channels."

    if channel in ("teams", "both"):
        if cfg and cfg.teams_webhook_url:
            fields = [("Status", "Operational"), ("Channel", "Microsoft Teams Webhook"), ("Sender", current_user.username)]
            success = send_teams_alert(cfg.teams_webhook_url, title, desc, severity="INFO", fields=fields)
            results["teams"] = "Sent successfully" if success else "Failed to send (check webhook URL)"
        else:
            results["teams"] = "Teams Webhook URL is not configured"

    if channel in ("email", "both"):
        if cfg and cfg.email_recipients:
            recipients = [e.strip() for e in cfg.email_recipients.split(",") if e.strip()]
            html = f"""
            <div style="font-family: Arial, sans-serif; background: #0f172a; color: #f8fafc; padding: 24px; border-radius: 8px;">
                <h2 style="color: #38bdf8;">🛡️ {title}</h2>
                <p>{desc}</p>
                <hr style="border: 1px solid #334155;" />
                <p style="font-size: 12px; color: #94a3b8;">Triggered by user: {current_user.username}</p>
            </div>
            """
            success = send_email_alert(recipients, title, html)
            results["email"] = "Sent successfully" if success else "Email dispatch simulated (SMTP server optional)"
        else:
            results["email"] = "Email recipients are not configured"

    return {
        "message": "Test alert execution completed",
        "results": results
    }
