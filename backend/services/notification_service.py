"""
Notification Service — Microsoft Teams & Email Alerts
Sends rich alert notifications via Teams Incoming Webhooks and SMTP email.
Includes deduplication logic to prevent spam (15-minute cooldown per alert type per server).
"""
import json
import logging
import os
import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import requests
from sqlalchemy.orm import Session

from models import Alert, AlertConfig

logger = logging.getLogger(__name__)

# Cooldown: don't resend same alert type for same server within this window
ALERT_COOLDOWN_MINUTES = 15


def _get_teams_webhook_url(db: Optional[Session] = None) -> Optional[str]:
    if db:
        try:
            cfg = db.query(AlertConfig).first()
            if cfg and cfg.teams_webhook_url:
                return cfg.teams_webhook_url.strip()
        except Exception:
            pass
    return os.getenv("TEAMS_WEBHOOK_URL")


def _get_smtp_config(db: Optional[Session] = None) -> dict:
    config = {
        "host": os.getenv("SMTP_HOST", ""),
        "port": int(os.getenv("SMTP_PORT", "587")),
        "user": os.getenv("SMTP_USER", ""),
        "password": os.getenv("SMTP_PASSWORD", ""),
        "to": os.getenv("ALERT_EMAIL_TO", ""),
    }
    if db:
        try:
            cfg = db.query(AlertConfig).first()
            if cfg:
                if cfg.smtp_host: config["host"] = cfg.smtp_host.strip()
                if cfg.smtp_port: config["port"] = cfg.smtp_port
                if cfg.smtp_user: config["user"] = cfg.smtp_user.strip()
                if cfg.smtp_password: config["password"] = cfg.smtp_password.strip()
                if cfg.email_to: config["to"] = cfg.email_to.strip()
        except Exception:
            pass
    return config


def _severity_color(severity: str) -> str:
    return {
        "critical": "#dc2626",
        "warning": "#f59e0b",
        "info": "#3b82f6",
    }.get(severity, "#6b7280")


def _severity_emoji(severity: str) -> str:
    return {
        "critical": "🔴",
        "warning": "🟡",
        "info": "🔵",
    }.get(severity, "⚪")


def send_teams_alert(alert: Alert, server_name: str = "Unknown", db: Optional[Session] = None):
    """Send a rich Adaptive Card message to Microsoft Teams / Slack via Incoming Webhook."""
    webhook_url = _get_teams_webhook_url(db)
    if not webhook_url:
        logger.debug("TEAMS_WEBHOOK_URL not configured, skipping Teams notification")
        return False

    emoji = _severity_emoji(alert.severity)
    color = _severity_color(alert.severity)

    # Teams Incoming Webhook expects a simple message card
    card = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": color.replace("#", ""),
        "summary": f"{emoji} {alert.type.upper()} Alert — {server_name}",
        "sections": [{
            "activityTitle": f"{emoji} **{alert.type.replace('_', ' ').upper()}** — {alert.severity.upper()}",
            "activitySubtitle": f"Server: **{server_name}**",
            "facts": [
                {"name": "Alert Type", "value": alert.type.replace("_", " ").title()},
                {"name": "Severity", "value": alert.severity.upper()},
                {"name": "Message", "value": alert.message},
                {"name": "Time", "value": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")},
            ],
            "markdown": True
        }]
    }

    try:
        resp = requests.post(webhook_url, json=card, timeout=10)
        if resp.status_code in (200, 202):
            logger.info(f"Teams alert sent: {alert.type} for {server_name}")
            return True
        else:
            logger.warning(f"Teams webhook returned {resp.status_code}: {resp.text[:200]}")
            return False
    except Exception as e:
        logger.error(f"Failed to send Teams alert: {e}")
        return False


def send_email_alert(alert: Alert, server_name: str = "Unknown"):
    """Send an HTML-formatted alert email via SMTP."""
    config = _get_smtp_config()
    if not all([config["host"], config["user"], config["password"], config["to"]]):
        logger.debug("SMTP not configured, skipping email notification")
        return False

    emoji = _severity_emoji(alert.severity)
    color = _severity_color(alert.severity)
    subject = f"{emoji} [{alert.severity.upper()}] {alert.type.replace('_', ' ').title()} — {server_name}"

    html_body = f"""
    <html>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f172a; color: #f1f5f9; padding: 24px;">
        <div style="max-width: 600px; margin: 0 auto; background: #1e293b; border-radius: 12px; border-left: 4px solid {color}; padding: 24px;">
            <h2 style="margin: 0 0 16px; color: {color};">
                {emoji} {alert.type.replace('_', ' ').upper()} — {alert.severity.upper()}
            </h2>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; color: #94a3b8; font-weight: 600;">Server</td>
                    <td style="padding: 8px 0; color: #f1f5f9;">{server_name}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #94a3b8; font-weight: 600;">Alert Type</td>
                    <td style="padding: 8px 0; color: #f1f5f9;">{alert.type.replace('_', ' ').title()}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #94a3b8; font-weight: 600;">Message</td>
                    <td style="padding: 8px 0; color: #f1f5f9;">{alert.message}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #94a3b8; font-weight: 600;">Time (UTC)</td>
                    <td style="padding: 8px 0; color: #f1f5f9;">{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}</td>
                </tr>
            </table>
            <hr style="border: 1px solid #334155; margin: 16px 0;" />
            <p style="font-size: 12px; color: #64748b;">AI Infrastructure Intelligence Platform — Automated Alert</p>
        </div>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = config["user"]
    msg["To"] = config["to"]
    msg.attach(MIMEText(alert.message, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(config["host"], config["port"], timeout=15) as smtp:
            smtp.starttls()
            smtp.login(config["user"], config["password"])
            smtp.send_message(msg)
        logger.info(f"Email alert sent: {alert.type} for {server_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email alert: {e}")
        return False


def dispatch_alert(db: Session, alert: Alert, server_name: str = "Unknown"):
    """
    Send alert via all configured channels (Teams + Email).
    Includes cooldown deduplication — won't resend same alert type for same server within ALERT_COOLDOWN_MINUTES.
    """
    # Check cooldown — did we recently send the same type of alert for this server?
    cutoff = datetime.utcnow() - timedelta(minutes=ALERT_COOLDOWN_MINUTES)
    recent = db.query(Alert).filter(
        Alert.server_id == alert.server_id,
        Alert.type == alert.type,
        Alert.notification_sent == True,
        Alert.created_at >= cutoff
    ).first()

    if recent:
        logger.debug(f"Alert cooldown active for {alert.type} on server {alert.server_id}, skipping notification")
        return

    teams_ok = send_teams_alert(alert, server_name, db)
    email_ok = send_email_alert(alert, server_name, db)

    now = datetime.utcnow()
    alert.notification_sent = True
    if teams_ok:
        alert.teams_sent_at = now
    if email_ok:
        alert.email_sent_at = now

    try:
        db.commit()
    except Exception as e:
        logger.warning(f"Failed to update alert notification status: {e}")
        db.rollback()


def create_and_dispatch_alert(
    db: Session,
    alert_type: str,
    severity: str,
    message: str,
    server_id: Optional[int] = None,
    site_id: Optional[int] = None,
    server_name: str = "Unknown"
):
    """Create an Alert record and dispatch notifications."""
    alert = Alert(
        server_id=server_id,
        site_id=site_id,
        type=alert_type,
        severity=severity,
        message=message,
    )
    db.add(alert)
    db.flush()

    dispatch_alert(db, alert, server_name)
    return alert
