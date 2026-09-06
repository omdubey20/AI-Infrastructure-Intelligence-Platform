"""
Notification Service — WhatsApp (User & Group) & Email Alerts
Sends rich alert notifications via WhatsApp (direct to user and/or team group) and SMTP email.
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


def _get_whatsapp_config(db: Optional[Session] = None) -> dict:
    """Retrieve WhatsApp notification configuration from database or environment."""
    config = {
        "enabled": True,
        "provider": os.getenv("WHATSAPP_PROVIDER", "callmebot"),
        "phone_number": os.getenv("WHATSAPP_PHONE_NUMBER", "").strip(),
        "group_id": os.getenv("WHATSAPP_GROUP_ID", "").strip(),
        "api_key": os.getenv("WHATSAPP_API_KEY", "").strip(),
        "account_sid": os.getenv("WHATSAPP_ACCOUNT_SID", "").strip(),
        "sender": os.getenv("WHATSAPP_SENDER", "").strip(),
        "api_url": os.getenv("WHATSAPP_API_URL", "").strip(),
    }
    if db:
        try:
            cfg = db.query(AlertConfig).first()
            if cfg:
                if cfg.whatsapp_enabled is not None:
                    config["enabled"] = bool(cfg.whatsapp_enabled)
                if cfg.whatsapp_provider:
                    config["provider"] = cfg.whatsapp_provider.strip()
                phone = getattr(cfg, "whatsapp_phone_number", None) or getattr(cfg, "whatsapp_phone", None)
                if phone:
                    config["phone_number"] = phone.strip()
                if cfg.whatsapp_group_id:
                    config["group_id"] = cfg.whatsapp_group_id.strip()
                if cfg.whatsapp_api_key:
                    config["api_key"] = cfg.whatsapp_api_key.strip()
                if cfg.whatsapp_account_sid:
                    config["account_sid"] = cfg.whatsapp_account_sid.strip()
                sender = getattr(cfg, "whatsapp_sender", None) or getattr(cfg, "whatsapp_from_phone", None)
                if sender:
                    config["sender"] = sender.strip()
                api_url = getattr(cfg, "whatsapp_api_url", None) or getattr(cfg, "whatsapp_gateway_url", None)
                if api_url:
                    config["api_url"] = api_url.strip()
        except Exception as e:
            logger.debug(f"Error fetching WhatsApp config from DB: {e}")
    return config


def _get_teams_webhook_url(db: Optional[Session] = None) -> Optional[str]:
    """Legacy Teams Webhook retrieval for backwards compatibility."""
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


def format_whatsapp_message(alert: Alert, server_name: str = "Unknown") -> str:
    """Format rich, easy-to-read alert message for WhatsApp."""
    emoji = _severity_emoji(alert.severity)
    sev_text = alert.severity.upper() if alert.severity else "INFO"
    alert_type = alert.type.replace("_", " ").title() if alert.type else "System Alert"
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    return (
        f"🚨 *INFRASTRUCTURE ALERT* 🚨\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"• *Status:* {emoji} *{sev_text}*\n"
        f"• *Type:* {alert_type}\n"
        f"• *Server:* {server_name}\n"
        f"• *Message:* {alert.message}\n"
        f"• *Time:* {timestamp}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ _AI Infrastructure Intelligence Platform_"
    )


def send_whatsapp_message(to: str, message: str, is_group: bool = False, config: Optional[dict] = None) -> bool:
    """
    Deliver WhatsApp message to phone number or group ID using selected provider.
    Supported providers: CallMeBot, Twilio, or Custom Gateway / Webhook.
    """
    if not to or not str(to).strip():
        return False

    target = str(to).strip()
    config = config or {}
    provider = (config.get("provider") or "callmebot").lower()
    api_key = config.get("api_key") or ""

    try:
        if provider == "twilio":
            account_sid = config.get("account_sid")
            sender = config.get("sender") or "whatsapp:+14155238886"
            if not account_sid or not api_key:
                logger.warning("Twilio WhatsApp requires account_sid and auth_token (api_key)")
                return False
            url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
            clean_to = target if target.startswith("whatsapp:") else f"whatsapp:{target}"
            clean_from = sender if sender.startswith("whatsapp:") else f"whatsapp:{sender}"
            resp = requests.post(
                url,
                auth=(account_sid, api_key),
                data={"From": clean_from, "To": clean_to, "Body": message},
                timeout=10
            )
            return resp.status_code in (200, 201)

        elif provider == "custom_gateway" or (config.get("api_url") and provider != "callmebot"):
            api_url = config.get("api_url")
            if not api_url:
                logger.warning("Custom WhatsApp gateway requires api_url")
                return False
            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
                headers["x-api-key"] = api_key
            payload = {
                "to": target,
                "recipient": target,
                "phone": target,
                "group_id": target if is_group else None,
                "message": message,
                "text": message,
                "is_group": is_group
            }
            resp = requests.post(api_url, json=payload, headers=headers, timeout=10)
            return resp.status_code in (200, 201, 202)

        else:
            # Default CallMeBot API (Personal phone or Group)
            base_url = "https://api.callmebot.com/whatsapp.php"
            params = {
                "text": message,
                "apikey": api_key
            }
            if is_group:
                params["group"] = target
            else:
                clean_phone = target.replace("+", "").replace(" ", "").replace("-", "")
                params["phone"] = clean_phone

            resp = requests.get(base_url, params=params, timeout=10)
            return resp.status_code == 200

    except Exception as e:
        logger.error(f"Failed to send WhatsApp message to {target} (is_group={is_group}): {e}")
        return False


def send_whatsapp_alert(
    alert: Alert,
    server_name: str = "Unknown",
    target: str = "all",
    db: Optional[Session] = None
) -> dict:
    """
    Send an alert to configured WhatsApp User, WhatsApp Group, or both.
    Returns status dict indicating delivery results.
    """
    config = _get_whatsapp_config(db)
    if not config.get("enabled", True):
        logger.debug("WhatsApp alerts disabled, skipping notification")
        return {"user_sent": False, "group_sent": False, "success": False, "detail": "WhatsApp alerts disabled"}

    phone = config.get("phone_number")
    group = config.get("group_id")

    if not phone and not group:
        logger.debug("Neither WhatsApp phone number nor group ID configured, skipping")
        return {"user_sent": False, "group_sent": False, "success": False, "detail": "No recipient configured"}

    msg = format_whatsapp_message(alert, server_name)
    user_ok = False
    group_ok = False

    if target in ("user", "all", "both") and phone:
        user_ok = send_whatsapp_message(phone, msg, is_group=False, config=config)
        if user_ok:
            logger.info(f"WhatsApp alert sent to user {phone} for {server_name}")

    if target in ("group", "all", "both") and group:
        group_ok = send_whatsapp_message(group, msg, is_group=True, config=config)
        if group_ok:
            logger.info(f"WhatsApp alert sent to group {group} for {server_name}")

    success = user_ok or group_ok
    return {
        "user_sent": user_ok,
        "group_sent": group_ok,
        "success": success,
        "detail": f"User: {'✓' if user_ok else ('Skipped' if not phone else 'Failed')}, Group: {'✓' if group_ok else ('Skipped' if not group else 'Failed')}"
    }


def send_teams_alert(alert: Alert, server_name: str = "Unknown", db: Optional[Session] = None) -> bool:
    """Send a card message to legacy Microsoft Teams / Slack incoming webhook if still configured."""
    webhook_url = _get_teams_webhook_url(db)
    if not webhook_url:
        return False

    emoji = _severity_emoji(alert.severity)
    color = _severity_color(alert.severity)

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
        return resp.status_code in (200, 202)
    except Exception as e:
        logger.error(f"Failed to send Teams alert: {e}")
        return False


def send_email_alert(alert: Alert, server_name: str = "Unknown", db: Optional[Session] = None) -> bool:
    """Send an HTML-formatted alert email via SMTP."""
    config = _get_smtp_config(db)
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
    Send alert via all configured channels (WhatsApp User & Group + Email + legacy Teams).
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

    whatsapp_res = send_whatsapp_alert(alert, server_name, target="all", db=db)
    teams_ok = send_teams_alert(alert, server_name, db=db)
    email_ok = send_email_alert(alert, server_name, db=db)

    now = datetime.utcnow()
    alert.notification_sent = True
    if whatsapp_res.get("success"):
        alert.whatsapp_sent_at = now
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
