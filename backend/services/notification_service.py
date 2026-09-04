"""
Notification Service — Microsoft Teams & Email Alerts
Sends rich alert notifications via Teams Incoming Webhooks and SMTP email.
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
    config = {
        "user_phone": os.getenv("WHATSAPP_USER_PHONE", ""),
        "group_id": os.getenv("WHATSAPP_GROUP_ID", ""),
        "provider": os.getenv("WHATSAPP_PROVIDER", "callmebot"),
        "api_key": os.getenv("WHATSAPP_API_KEY", ""),
        "account_sid": os.getenv("WHATSAPP_ACCOUNT_SID", ""),
        "from_number": os.getenv("WHATSAPP_FROM_NUMBER", ""),
        "gateway_url": os.getenv("WHATSAPP_GATEWAY_URL", ""),
        "enabled": True,
        "send_user": True,
        "send_group": True,
    }
    if db:
        try:
            cfg = db.query(AlertConfig).first()
            if cfg:
                if cfg.whatsapp_user_phone: config["user_phone"] = cfg.whatsapp_user_phone.strip()
                if cfg.whatsapp_group_id: config["group_id"] = cfg.whatsapp_group_id.strip()
                if cfg.whatsapp_provider: config["provider"] = cfg.whatsapp_provider.strip()
                if cfg.whatsapp_api_key: config["api_key"] = cfg.whatsapp_api_key.strip()
                if cfg.whatsapp_account_sid: config["account_sid"] = cfg.whatsapp_account_sid.strip()
                if cfg.whatsapp_from_number: config["from_number"] = cfg.whatsapp_from_number.strip()
                if cfg.whatsapp_gateway_url: config["gateway_url"] = cfg.whatsapp_gateway_url.strip()
                if cfg.whatsapp_enabled is not None: config["enabled"] = bool(cfg.whatsapp_enabled)
                if cfg.whatsapp_send_user is not None: config["send_user"] = bool(cfg.whatsapp_send_user)
                if cfg.whatsapp_send_group is not None: config["send_group"] = bool(cfg.whatsapp_send_group)
        except Exception:
            pass
    return config


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


def send_whatsapp_alert(alert: Alert, server_name: str = "Unknown", db: Optional[Session] = None) -> bool:
    """
    Send formatted WhatsApp alert to configured User Phone Number and/or WhatsApp Group.
    Supports CallMeBot, Twilio WhatsApp, or custom HTTP Gateway.
    """
    config = _get_whatsapp_config(db)
    if not config.get("enabled", True):
        logger.debug("WhatsApp notifications disabled in settings")
        return False

    user_phone = config.get("user_phone", "").strip()
    group_id = config.get("group_id", "").strip()
    api_key = config.get("api_key", "").strip()
    provider = config.get("provider", "callmebot").lower()

    if not user_phone and not group_id:
        logger.debug("No WhatsApp user phone or group ID configured, skipping")
        return False

    emoji = _severity_emoji(alert.severity)
    type_label = alert.type.replace("_", " ").upper()
    sev_label = alert.severity.upper()
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    text = (
        f"🚨 *INFRASTRUCTURE ALERT* 🚨\n\n"
        f"{emoji} *{sev_label}* — *{type_label}*\n"
        f"🖥️ *Server:* {server_name}\n"
        f"📝 *Message:* {alert.message}\n"
        f"⏱️ *Time:* {now_str}\n\n"
        f"_AI Infrastructure Intelligence Platform_"
    )

    success = False

    # 1. Twilio WhatsApp Provider
    if provider == "twilio":
        account_sid = config.get("account_sid", "").strip()
        from_num = config.get("from_number", "").strip() or "+14155238886"
        if not from_num.startswith("+") and not from_num.startswith("whatsapp:"):
            from_num = f"+{from_num}"
        if not from_num.startswith("whatsapp:"):
            from_num = f"whatsapp:{from_num}"

        if account_sid and api_key:
            twilio_url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
            auth = (account_sid, api_key)

            # Send to User
            if user_phone and config.get("send_user", True):
                u_target = user_phone if user_phone.startswith("whatsapp:") else f"whatsapp:{user_phone if user_phone.startswith('+') else '+' + user_phone}"
                try:
                    r = requests.post(twilio_url, auth=auth, data={"From": from_num, "To": u_target, "Body": text}, timeout=10)
                    if r.status_code in (200, 201):
                        logger.info(f"Twilio WhatsApp alert sent to user {user_phone}")
                        success = True
                    else:
                        logger.warning(f"Twilio user dispatch returned {r.status_code}: {r.text[:150]}")
                except Exception as e:
                    logger.error(f"Failed Twilio WhatsApp send to user: {e}")

            # Send to Group
            if group_id and config.get("send_group", True):
                g_target = group_id if group_id.startswith("whatsapp:") else f"whatsapp:{group_id}"
                try:
                    r = requests.post(twilio_url, auth=auth, data={"From": from_num, "To": g_target, "Body": text}, timeout=10)
                    if r.status_code in (200, 201):
                        logger.info(f"Twilio WhatsApp alert sent to group {group_id}")
                        success = True
                    else:
                        logger.warning(f"Twilio group dispatch returned {r.status_code}: {r.text[:150]}")
                except Exception as e:
                    logger.error(f"Failed Twilio WhatsApp send to group: {e}")

    # 2. Custom Gateway / Webhook Provider
    elif provider == "gateway":
        gateway_url = config.get("gateway_url", "").strip()
        if gateway_url:
            payload = {
                "user_phone": user_phone if config.get("send_user", True) else None,
                "group_id": group_id if config.get("send_group", True) else None,
                "message": text,
                "server_name": server_name,
                "alert_type": alert.type,
                "severity": alert.severity,
            }
            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            try:
                r = requests.post(gateway_url, json=payload, headers=headers, timeout=10)
                if r.status_code in (200, 201, 202):
                    logger.info(f"WhatsApp gateway alert sent via {gateway_url}")
                    success = True
                else:
                    logger.warning(f"WhatsApp gateway returned {r.status_code}: {r.text[:150]}")
            except Exception as e:
                logger.error(f"Failed WhatsApp gateway send: {e}")

    # 3. CallMeBot Provider (Default / Free developer API for user & group)
    else:
        encoded_text = urllib.parse.quote(text)
        
        # Send to User
        if user_phone and config.get("send_user", True):
            clean_phone = user_phone.replace("+", "").replace(" ", "").replace("-", "")
            url = f"https://api.callmebot.com/whatsapp.php?phone={clean_phone}&text={encoded_text}&apikey={api_key}"
            try:
                r = requests.get(url, timeout=10)
                if r.status_code == 200 and "error" not in r.text.lower():
                    logger.info(f"CallMeBot WhatsApp alert sent to user {user_phone}")
                    success = True
                else:
                    logger.warning(f"CallMeBot user dispatch returned {r.status_code}: {r.text[:150]}")
            except Exception as e:
                logger.error(f"Failed CallMeBot send to user: {e}")

        # Send to Group
        if group_id and config.get("send_group", True):
            clean_group = urllib.parse.quote(group_id.strip())
            url = f"https://api.callmebot.com/whatsapp.php?source=php&group={clean_group}&text={encoded_text}&apikey={api_key}"
            try:
                r = requests.get(url, timeout=10)
                if r.status_code == 200 and "error" not in r.text.lower():
                    logger.info(f"CallMeBot WhatsApp alert sent to group {group_id}")
                    success = True
                else:
                    logger.warning(f"CallMeBot group dispatch returned {r.status_code}: {r.text[:150]}")
            except Exception as e:
                logger.error(f"Failed CallMeBot send to group: {e}")

    return success


def dispatch_alert(db: Session, alert: Alert, server_name: str = "Unknown"):
    """
    Send alert via configured channels (WhatsApp + Email + Teams).
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

    whatsapp_ok = send_whatsapp_alert(alert, server_name, db)
    teams_ok = send_teams_alert(alert, server_name, db)
    email_ok = send_email_alert(alert, server_name, db)

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
