"""
Enterprise Multi-Channel Alerting Service
- Microsoft Teams Incoming Webhook (Adaptive Cards)
- SMTP Email Alerts
- Rate limiting & Alert Deduplication
"""
import logging
import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import requests

logger = logging.getLogger("alerting_service")

# Global in-memory deduplication cache: {alert_key: last_sent_timestamp}
_alert_cache = {}
DEDUP_WINDOW_SECONDS = 300  # 5 minutes per unique alert signature


def get_alert_config(db):
    """Retrieve or initialize default alert configuration."""
    from models import AlertConfig
    try:
        config = db.query(AlertConfig).first()
        if not config:
            config = AlertConfig(
                teams_webhook_url=os.getenv("TEAMS_WEBHOOK_URL"),
                teams_enabled=bool(os.getenv("TEAMS_WEBHOOK_URL")),
                email_recipients=os.getenv("ALERT_EMAIL_RECIPIENTS"),
                email_enabled=bool(os.getenv("ALERT_EMAIL_RECIPIENTS")),
                alert_on_disk_full=True,
                alert_on_website_down=True,
                alert_on_malware=True,
            )
            db.add(config)
            db.commit()
            db.refresh(config)
        return config
    except Exception as e:
        logger.warning(f"Error fetching alert config: {e}")
        return None


def send_teams_alert(webhook_url: str, title: str, description: str, severity: str = "WARNING", fields: list = None) -> bool:
    """Send formatted Adaptive Card to Microsoft Teams Webhook."""
    if not webhook_url:
        return False

    theme_color = "FF0000" if severity == "CRITICAL" else ("FFA500" if severity == "WARNING" else "0076D7")

    facts = []
    if fields:
        for k, v in fields:
            facts.append({"name": k, "value": str(v)})
    facts.append({"name": "Timestamp", "value": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")})
    facts.append({"name": "Severity", "value": severity})

    payload = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": theme_color,
        "summary": title,
        "sections": [{
            "activityTitle": f"🛡️ Infra Intel: {title}",
            "activitySubtitle": f"Severity: {severity} · Infrastructure Intelligence Platform",
            "text": description,
            "facts": facts,
            "markdown": True
        }]
    }

    try:
        res = requests.post(webhook_url, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
        if res.status_code in (200, 201, 202):
            logger.info(f"Teams alert dispatched: {title}")
            return True
        else:
            logger.warning(f"Teams webhook returned status {res.status_code}: {res.text}")
            return False
    except Exception as e:
        logger.error(f"Failed to post Teams webhook: {e}")
        return False


def send_email_alert(recipients: list, subject: str, html_body: str) -> bool:
    """Send HTML alert email via SMTP."""
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASSWORD")
    sender_email = os.getenv("SMTP_FROM", smtp_user or "alerts@infra-intel.local")

    if not (smtp_host and recipients):
        logger.info(f"Email alert skipped (SMTP not configured). Subject: {subject}")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[Infra Intel Alert] {subject}"
    msg["From"] = sender_email
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.starttls()
            if smtp_user and smtp_pass:
                server.login(smtp_user, smtp_pass)
            server.sendmail(sender_email, recipients, msg.as_string())
        logger.info(f"Email alert sent to {recipients}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email alert: {e}")
        return False


def notify_alert(db, category: str, target_name: str, title: str, description: str, severity: str = "WARNING", target_type: str = "server", target_id: int = None, recommendation: str = None) -> bool:
    """
    Unified alerting trigger:
    1. Deduplicates alerts (prevents spam within DEDUP_WINDOW_SECONDS).
    2. Saves SecurityAlert record in PostgreSQL database.
    3. Dispatches to Teams & Email if enabled.
    """
    from models import SecurityAlert

    alert_key = f"{category}:{target_name}:{title}"
    now = datetime.utcnow()
    if alert_key in _alert_cache:
        last_sent = _alert_cache[alert_key]
        if (now - last_sent).total_seconds() < DEDUP_WINDOW_SECONDS:
            logger.debug(f"Alert throttled (duplicate): {alert_key}")
            return False

    _alert_cache[alert_key] = now

    # 1. Deduplicate & Record/Update SecurityAlert in Database
    try:
        existing_alert = db.query(SecurityAlert).filter(
            SecurityAlert.target_name == target_name,
            SecurityAlert.category == category,
            SecurityAlert.is_resolved == False
        ).first()

        if existing_alert:
            existing_alert.title = title
            existing_alert.description = description
            existing_alert.severity = severity
            if recommendation:
                existing_alert.recommendation = recommendation
            db.commit()
        else:
            alert = SecurityAlert(
                target_type=target_type,
                target_id=target_id,
                target_name=target_name,
                severity=severity,
                category=category,
                title=title,
                description=description,
                recommendation=recommendation or "Investigate and resolve infrastructure risk.",
                is_resolved=False,
                created_at=now,
            )
            db.add(alert)
            db.commit()
    except Exception as e:
        logger.warning(f"Failed to record SecurityAlert in database: {e}")
        db.rollback()

    # 2. Check Alert Config & Dispatch
    config = get_alert_config(db)
    if not config:
        return True

    # Teams Dispatch
    if config.teams_enabled and config.teams_webhook_url:
        fields = [("Target", target_name), ("Category", category), ("Recommendation", recommendation or "Review platform dashboard")]
        send_teams_alert(config.teams_webhook_url, f"[{severity}] {title}", description, severity=severity, fields=fields)

    # Email Dispatch
    if config.email_enabled and config.email_recipients:
        recipients = [e.strip() for e in config.email_recipients.split(",") if e.strip()]
        if recipients:
            html = f"""
            <div style="font-family: Arial, sans-serif; background: #0f172a; color: #f8fafc; padding: 24px; border-radius: 8px;">
                <h2 style="color: {'#ef4444' if severity == 'CRITICAL' else '#f59e0b'};">⚠️ {title}</h2>
                <p><strong>Target:</strong> {target_name} ({target_type})</p>
                <p><strong>Severity:</strong> <span style="background: {'#7f1d1d' if severity == 'CRITICAL' else '#78350f'}; padding: 4px 8px; border-radius: 4px;">{severity}</span></p>
                <p><strong>Category:</strong> {category}</p>
                <div style="background: #1e293b; padding: 16px; border-radius: 6px; margin: 16px 0;">
                    <p style="margin: 0; color: #cbd5e1;">{description}</p>
                </div>
                <p><strong>Recommendation:</strong> {recommendation or 'Please inspect server status immediately.'}</p>
                <hr style="border: 1px solid #334155;" />
                <p style="font-size: 12px; color: #94a3b8;">AI Infrastructure Intelligence Platform · 24/7 Security & Uptime Sentinel</p>
            </div>
            """
            send_email_alert(recipients, f"[{severity}] {title} ({target_name})", html)

    return True
