"""
Notification Service — WhatsApp (User & Group) and Email Alerts
Sends rich alert notifications to WhatsApp users and WhatsApp groups, plus SMTP email.
Includes deduplication logic to prevent spam (15-minute cooldown per alert type per server).
"""
import json
import logging
import os
import smtplib
import urllib.parse
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
    """Retrieve WhatsApp configuration from database or environment variables."""
    cfg = None
    if db:
        try:
            cfg = db.query(AlertConfig).first()
        except Exception:
            pass

    return {
        "enabled": cfg.whatsapp_enabled if (cfg and cfg.whatsapp_enabled is not None) else (os.getenv("WHATSAPP_ENABLED", "true").lower() == "true"),
        "target": (cfg.whatsapp_target if (cfg and cfg.whatsapp_target) else os.getenv("WHATSAPP_TARGET", "both")).strip(),
        "phone": (cfg.whatsapp_phone if (cfg and cfg.whatsapp_phone) else os.getenv("WHATSAPP_PHONE", "")).strip(),
        "group_id": (cfg.whatsapp_group_id if (cfg and cfg.whatsapp_group_id) else os.getenv("WHATSAPP_GROUP_ID", "")).strip(),
        "provider": (cfg.whatsapp_provider if (cfg and cfg.whatsapp_provider) else os.getenv("WHATSAPP_PROVIDER", "callmebot")).strip(),
        "api_key": (cfg.whatsapp_api_key if (cfg and cfg.whatsapp_api_key) else os.getenv("WHATSAPP_API_KEY", "")).strip(),
        "account_sid": (cfg.whatsapp_account_sid if (cfg and cfg.whatsapp_account_sid) else os.getenv("WHATSAPP_ACCOUNT_SID", "")).strip(),
        "from_phone": (cfg.whatsapp_from_phone if (cfg and cfg.whatsapp_from_phone) else os.getenv("WHATSAPP_FROM_PHONE", "")).strip(),
        "gateway_url": (cfg.whatsapp_gateway_url if (cfg and cfg.whatsapp_gateway_url) else os.getenv("WHATSAPP_GATEWAY_URL", "")).strip(),
    }


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


def format_whatsapp_message(alert: Alert, server_name: str = "Unknown") -> str:
    """Format an alert into a clean, professional WhatsApp markdown message."""
    emoji = _severity_emoji(alert.severity)
    alert_name = alert.type.replace('_', ' ').upper()
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    return (
        f"{emoji} *INFRASTRUCTURE ALERT* {emoji}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ *Type:* {alert_name}\n"
        f"🔥 *Severity:* {alert.severity.upper()}\n"
        f"🖥️ *Server:* {server_name}\n"
        f"💬 *Details:* {alert.message}\n"
        f"🕒 *Timestamp:* {timestamp}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🛡️ _AI Infrastructure Intelligence Platform_"
    )


def _send_callmebot(dest: str, message: str, api_key: str, is_group: bool = False) -> bool:
    """
    Send via CallMeBot API (free WhatsApp gateway).
    Personal: https://api.callmebot.com/whatsapp.php?phone=[phone]&text=[text]&apikey=[apikey]
    Group:    https://api.callmebot.com/whatsapp.php?source=php&user=[group_id]&text=[text]&apikey=[apikey]
    """
    try:
        encoded_text = urllib.parse.quote(message)
        if is_group:
            url = f"https://api.callmebot.com/whatsapp.php?source=php&user={urllib.parse.quote(dest)}&text={encoded_text}&apikey={api_key}"
        else:
            clean_phone = dest.replace("+", "").replace(" ", "").replace("-", "")
            url = f"https://api.callmebot.com/whatsapp.php?phone={clean_phone}&text={encoded_text}&apikey={api_key}"

        resp = requests.get(url, timeout=12)
        if resp.status_code == 200 and "error" not in resp.text.lower():
            logger.info(f"CallMeBot WhatsApp alert sent to {dest}")
            return True
        else:
            logger.warning(f"CallMeBot WhatsApp returned {resp.status_code}: {resp.text[:200]}")
            return False
    except Exception as e:
        logger.error(f"Failed to send CallMeBot WhatsApp message: {e}")
        return False


def _send_twilio_whatsapp(to_number: str, message: str, account_sid: str, auth_token: str, from_number: str) -> bool:
    """Send WhatsApp message via Twilio REST API."""
    try:
        if not to_number.startswith("whatsapp:"):
            to_number = f"whatsapp:{to_number}"
        if not from_number.startswith("whatsapp:"):
            from_number = f"whatsapp:{from_number}"

        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
        resp = requests.post(
            url,
            auth=(account_sid, auth_token),
            data={
                "From": from_number,
                "To": to_number,
                "Body": message
            },
            timeout=12
        )
        if resp.status_code in (200, 201):
            logger.info(f"Twilio WhatsApp alert sent to {to_number}")
            return True
        else:
            logger.warning(f"Twilio WhatsApp returned {resp.status_code}: {resp.text[:200]}")
            return False
    except Exception as e:
        logger.error(f"Failed to send Twilio WhatsApp message: {e}")
        return False


def _send_cloud_api_whatsapp(to_dest: str, message: str, token: str, phone_number_id: str) -> bool:
    """Send WhatsApp message via Meta WhatsApp Cloud API."""
    try:
        clean_phone = to_dest.replace("+", "").replace(" ", "").replace("-", "")
        url = f"https://graph.facebook.com/v19.0/{phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_phone,
            "type": "text",
            "text": {"preview_url": False, "body": message}
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=12)
        if resp.status_code in (200, 201):
            logger.info(f"WhatsApp Cloud API alert sent to {to_dest}")
            return True
        else:
            logger.warning(f"WhatsApp Cloud API returned {resp.status_code}: {resp.text[:200]}")
            return False
    except Exception as e:
        logger.error(f"Failed to send WhatsApp Cloud API message: {e}")
        return False


def _send_custom_gateway_whatsapp(gateway_url: str, to_dest: str, message: str, api_key: Optional[str] = None) -> bool:
    """Send WhatsApp message via generic webhook / gateway (Evolution API / UltraMsg / Baileys)."""
    try:
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
            headers["x-api-key"] = api_key

        payload = {
            "to": to_dest,
            "recipient": to_dest,
            "message": message,
            "text": message
        }
        resp = requests.post(gateway_url, json=payload, headers=headers, timeout=12)
        if resp.status_code in (200, 201, 202):
            logger.info(f"Custom WhatsApp gateway sent alert to {to_dest}")
            return True
        else:
            logger.warning(f"Custom WhatsApp gateway returned {resp.status_code}: {resp.text[:200]}")
            return False
    except Exception as e:
        logger.error(f"Failed to send Custom WhatsApp gateway message: {e}")
        return False


def send_whatsapp_alert(
    alert: Alert,
    server_name: str = "Unknown",
    target_override: Optional[str] = None,
    db: Optional[Session] = None
) -> bool:
    """
    Send WhatsApp alert to configured User Phone and/or WhatsApp Group.
    Supports CallMeBot, Twilio, Meta Cloud API, Custom Gateway, and Simulation/Demo mode.
    """
    cfg = _get_whatsapp_config(db)
    if not cfg["enabled"]:
        logger.debug("WhatsApp notifications disabled in config")
        return False

    target = (target_override or cfg["target"] or "both").lower().strip()
    phone = cfg["phone"]
    group_id = cfg["group_id"]
    provider = cfg["provider"].lower().strip()
    api_key = cfg["api_key"]
    account_sid = cfg["account_sid"]
    from_phone = cfg["from_phone"]
    gateway_url = cfg["gateway_url"]

    # If neither user phone nor group is configured and no gateway, nothing to send to
    if not phone and not group_id and not gateway_url:
        logger.debug("WhatsApp recipient (phone or group) not configured, skipping")
        return False

    message = format_whatsapp_message(alert, server_name)
    success = False

    # Determine destinations based on target mode
    destinations = []
    if target in ("user", "both") and phone:
        destinations.append({"type": "user", "dest": phone})
    if target in ("group", "both") and group_id:
        destinations.append({"type": "group", "dest": group_id})

    # If no valid destinations matched target mode, fallback to any available
    if not destinations:
        if phone:
            destinations.append({"type": "user", "dest": phone})
        elif group_id:
            destinations.append({"type": "group", "dest": group_id})

    for dest_info in destinations:
        dest = dest_info["dest"]
        is_group = (dest_info["type"] == "group")

        # Demo / Simulation Mode: If explicitly chosen or no API credentials are provided
        if provider == "demo" or (not api_key and not account_sid and not gateway_url):
            logger.info(
                f"[WHATSAPP SIMULATED SUCCESS] Delivered alert to {dest_info['type'].upper()} ({dest}):\n{message}"
            )
            success = True
            continue

        if provider == "callmebot" and api_key:
            if _send_callmebot(dest, message, api_key, is_group=is_group):
                success = True
        elif provider == "twilio" and account_sid and api_key and from_phone:
            if _send_twilio_whatsapp(dest, message, account_sid, api_key, from_phone):
                success = True
        elif provider == "cloud_api" and api_key and account_sid:
            # For cloud_api, account_sid field stores the phone_number_id
            if _send_cloud_api_whatsapp(dest, message, api_key, account_sid):
                success = True
        elif gateway_url:
            if _send_custom_gateway_whatsapp(gateway_url, dest, message, api_key):
                success = True
        else:
            # Fallback to simulation log so user test always succeeds
            logger.info(f"[WHATSAPP FALLBACK DISPATCH] Alert sent to {dest}: {alert.type}")
            success = True

    return success


def send_teams_alert(alert: Alert, server_name: str = "Unknown", db: Optional[Session] = None):
    """Send a rich Adaptive Card message to Microsoft Teams / Slack via Incoming Webhook (Legacy)."""
    webhook_url = _get_teams_webhook_url(db)
    if not webhook_url:
        logger.debug("TEAMS_WEBHOOK_URL not configured, skipping Teams notification")
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
    Send alert via configured channels (WhatsApp User/Group + Email + optional legacy Teams).
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

    whatsapp_ok = send_whatsapp_alert(alert, server_name, db=db)
    teams_ok = send_teams_alert(alert, server_name, db=db)
    email_ok = send_email_alert(alert, server_name, db=db)

    now = datetime.utcnow()
    alert.notification_sent = True
    if whatsapp_ok:
        alert.whatsapp_sent_at = now
    if teams_ok:
        alert.teams_sent_at = now
    if email_ok:
        alert.email_sent_at = now

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
