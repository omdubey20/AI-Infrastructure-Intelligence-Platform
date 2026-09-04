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


def _get_whatsapp_config(db: Optional[Session] = None) -> dict:
    config = {
        "enabled": True,
        "user_phone": os.getenv("WHATSAPP_USER_PHONE", ""),
        "group_id": os.getenv("WHATSAPP_GROUP_ID", ""),
        "provider": os.getenv("WHATSAPP_PROVIDER", "callmebot"),
        "api_key": os.getenv("WHATSAPP_API_KEY", ""),
        "api_url": os.getenv("WHATSAPP_API_URL", ""),
    }
    if db:
        try:
            cfg = db.query(AlertConfig).first()
            if cfg:
                if cfg.whatsapp_enabled is not None:
                    config["enabled"] = cfg.whatsapp_enabled
                if cfg.whatsapp_user_phone:
                    config["user_phone"] = cfg.whatsapp_user_phone.strip()
                if cfg.whatsapp_group_id:
                    config["group_id"] = cfg.whatsapp_group_id.strip()
                if cfg.whatsapp_provider:
                    config["provider"] = cfg.whatsapp_provider.strip()
                if cfg.whatsapp_api_key:
                    config["api_key"] = cfg.whatsapp_api_key.strip()
                if cfg.whatsapp_api_url:
                    config["api_url"] = cfg.whatsapp_api_url.strip()
        except Exception as e:
            logger.debug(f"Failed to load WhatsApp config from DB: {e}")
    return config


def _deliver_whatsapp_message(recipient: str, is_group: bool, text: str, provider: str, api_key: str, api_url: str) -> bool:
    try:
        if provider == "callmebot":
            base = "https://api.callmebot.com/whatsapp.php"
            if is_group:
                params = {
                    "source": "group",
                    "group_id": recipient,
                    "text": text,
                    "apikey": api_key,
                }
            else:
                phone = recipient.replace("+", "")
                params = {
                    "phone": phone,
                    "text": text,
                    "apikey": api_key,
                }
            resp = requests.get(base, params=params, timeout=12)
            if resp.status_code in (200, 201) and "error" not in resp.text.lower():
                logger.info(f"CallMeBot WhatsApp delivered to {'group' if is_group else 'user'} {recipient}")
                return True
            else:
                logger.warning(f"CallMeBot response ({resp.status_code}): {resp.text[:150]}")
                return resp.status_code in (200, 201)

        elif provider == "twilio":
            sid = os.getenv("TWILIO_ACCOUNT_SID", "")
            token = api_key or os.getenv("TWILIO_AUTH_TOKEN", "")
            from_number = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
            to_number = recipient if recipient.startswith("whatsapp:") else f"whatsapp:{recipient}"
            url = api_url or f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
            
            resp = requests.post(
                url,
                data={"From": from_number, "To": to_number, "Body": text},
                auth=(sid, token),
                timeout=12
            )
            return resp.status_code in (200, 201)

        else:
            # Custom Gateway / Webhook / Green-API / UltraMsg
            url = api_url or "https://api.whatsapp.com/send"
            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
                headers["x-api-key"] = api_key
            payload = {
                "to": recipient,
                "recipient": recipient,
                "is_group": is_group,
                "group_id": recipient if is_group else None,
                "phone": recipient if not is_group else None,
                "message": text,
                "text": text,
            }
            resp = requests.post(url, json=payload, headers=headers, timeout=12)
            return resp.status_code in (200, 201, 202)
    except Exception as e:
        logger.error(f"WhatsApp delivery error to {recipient}: {e}")
        return False


def send_whatsapp_alert(
    alert: Alert,
    server_name: str = "Unknown",
    target: str = "both",  # "user", "group", or "both"
    db: Optional[Session] = None,
) -> dict:
    """Send a formatted WhatsApp alert to configured WhatsApp user and/or group."""
    config = _get_whatsapp_config(db)
    if not config["enabled"]:
        logger.debug("WhatsApp notifications are disabled in settings")
        return {"user_sent": False, "group_sent": False, "error": "WhatsApp alerts disabled"}

    user_phone = config["user_phone"]
    group_id = config["group_id"]
    provider = config.get("provider", "callmebot").lower()
    api_key = config["api_key"]
    api_url = config["api_url"]

    emoji = _severity_emoji(alert.severity)
    alert_title = alert.type.replace('_', ' ').upper()
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    text_lines = [
        f"{emoji} *INFRASTRUCTURE ALERT: {alert_title}*",
        "━━━━━━━━━━━━━━━━━━━━",
        f"📊 *Severity:* {alert.severity.upper()}",
        f"🖥️ *Target:* {server_name}",
        f"⚠️ *Details:* {alert.message}",
        f"⏰ *Time:* {now_str}",
        "━━━━━━━━━━━━━━━━━━━━",
        "AI Infrastructure Intelligence Platform"
    ]
    message_text = "\n".join(text_lines)

    result = {"user_sent": False, "group_sent": False, "errors": []}

    # Send to User Phone
    if target in ("both", "user") and user_phone:
        phones = [p.strip() for p in user_phone.split(",") if p.strip()]
        for phone in phones:
            phone_clean = phone.replace(" ", "").replace("-", "")
            if not phone_clean.startswith("+") and not phone_clean.startswith("whatsapp:"):
                phone_clean = "+" + phone_clean
            
            sent = _deliver_whatsapp_message(
                recipient=phone_clean,
                is_group=False,
                text=message_text,
                provider=provider,
                api_key=api_key,
                api_url=api_url,
            )
            if sent:
                result["user_sent"] = True
            else:
                result["errors"].append(f"Failed delivery to user {phone}")

    # Send to WhatsApp Group
    if target in ("both", "group") and group_id:
        group_clean = group_id.strip()
        sent = _deliver_whatsapp_message(
            recipient=group_clean,
            is_group=True,
            text=message_text,
            provider=provider,
            api_key=api_key,
            api_url=api_url,
        )
        if sent:
            result["group_sent"] = True
        else:
            result["errors"].append(f"Failed delivery to group {group_clean}")

    return result


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


def send_email_alert(alert: Alert, server_name: str = "Unknown", db: Optional[Session] = None):
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
    Send alert via all configured channels (WhatsApp User & Group, Email, Teams).
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

    # Dispatch to WhatsApp (User & Group), Email, and Teams
    wa_result = send_whatsapp_alert(alert, server_name, target="both", db=db)
    whatsapp_ok = wa_result.get("user_sent") or wa_result.get("group_sent")
    email_ok = send_email_alert(alert, server_name, db)
    teams_ok = send_teams_alert(alert, server_name, db)

    now = datetime.utcnow()
    alert.notification_sent = True
    if whatsapp_ok:
        alert.whatsapp_sent_at = now
    if email_ok:
        alert.email_sent_at = now
    if teams_ok:
        alert.teams_sent_at = now

    try:
        db.flush()
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
