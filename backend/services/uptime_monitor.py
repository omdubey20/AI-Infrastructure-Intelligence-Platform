"""
Uptime Monitor Service
Checks all discovered project domains for HTTP availability every 60 seconds.
Records UptimeCheck records and creates/resolves alerts on state changes.
"""
import logging
import os
import socket
import ssl
import time
from datetime import datetime, timedelta
from typing import Optional

import requests
from sqlalchemy.orm import Session

from database import get_db
from models import ProjectDiscovery, UptimeCheck, Alert, Server
from services.notification_service import create_and_dispatch_alert

logger = logging.getLogger(__name__)

# Timeout for HTTP checks
HTTP_TIMEOUT = 15
# How many consecutive failures before alerting
FAILURE_THRESHOLD = 2


def check_single_site(url: str) -> dict:
    """Perform an HTTP GET check on a single URL. Returns check result dict."""
    result = {
        "is_up": False,
        "http_status": None,
        "response_time_ms": None,
        "error_message": None,
        "ssl_valid": None,
        "ssl_expiry_days": None,
    }

    try:
        start = time.monotonic()
        resp = requests.get(
            url,
            timeout=HTTP_TIMEOUT,
            allow_redirects=True,
            headers={"User-Agent": "InfraIntel-UptimeMonitor/1.0"},
            verify=True,
        )
        elapsed_ms = int((time.monotonic() - start) * 1000)

        result["http_status"] = resp.status_code
        result["response_time_ms"] = elapsed_ms
        result["is_up"] = 200 <= resp.status_code < 500  # 5xx = server error = down
        result["ssl_valid"] = True  # If we got here with verify=True, SSL is valid

    except requests.exceptions.SSLError as e:
        result["error_message"] = f"SSL Error: {str(e)[:200]}"
        result["ssl_valid"] = False
        # Try without SSL verification to still get status
        try:
            start = time.monotonic()
            resp = requests.get(url, timeout=HTTP_TIMEOUT, allow_redirects=True, verify=False,
                                headers={"User-Agent": "InfraIntel-UptimeMonitor/1.0"})
            result["http_status"] = resp.status_code
            result["response_time_ms"] = int((time.monotonic() - start) * 1000)
            result["is_up"] = 200 <= resp.status_code < 500
        except Exception:
            pass

    except requests.exceptions.ConnectionError as e:
        result["error_message"] = f"Connection Error: {str(e)[:200]}"
    except requests.exceptions.Timeout:
        result["error_message"] = f"Timeout after {HTTP_TIMEOUT}s"
    except Exception as e:
        result["error_message"] = f"Error: {str(e)[:200]}"

    # Check SSL expiry independently
    if url.startswith("https://"):
        try:
            hostname = url.split("//")[1].split("/")[0].split(":")[0]
            ctx = ssl.create_default_context()
            with ctx.wrap_socket(socket.socket(), server_hostname=hostname) as s:
                s.settimeout(5)
                s.connect((hostname, 443))
                cert = s.getpeercert()
                not_after = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
                result["ssl_expiry_days"] = (not_after - datetime.utcnow()).days
                result["ssl_valid"] = result["ssl_expiry_days"] > 0
        except Exception:
            pass

    return result


def _get_previous_state(db: Session, site_id: int) -> Optional[bool]:
    """Get the last known up/down state for a site."""
    last = db.query(UptimeCheck).filter(
        UptimeCheck.site_id == site_id
    ).order_by(UptimeCheck.checked_at.desc()).first()
    return last.is_up if last else None


def _count_recent_failures(db: Session, site_id: int) -> int:
    """Count consecutive recent failures for a site."""
    recent = db.query(UptimeCheck).filter(
        UptimeCheck.site_id == site_id
    ).order_by(UptimeCheck.checked_at.desc()).limit(FAILURE_THRESHOLD).all()

    count = 0
    for check in recent:
        if not check.is_up:
            count += 1
        else:
            break
    return count


def run_uptime_checks(db: Session):
    """Run uptime checks for all discovered projects with domains."""
    discoveries = db.query(ProjectDiscovery).filter(
        ProjectDiscovery.domain.isnot(None),
        ProjectDiscovery.domain != "",
        ProjectDiscovery.is_live == True,
    ).all()

    checked = 0
    for disc in discoveries:
        domain = disc.domain.strip()
        if not domain:
            continue

        # Build URL — try HTTPS first
        url = f"https://{domain}" if not domain.startswith("http") else domain

        result = check_single_site(url)

        # Record the check
        check = UptimeCheck(
            site_id=disc.id,
            server_id=disc.server_id,
            url=url,
            is_up=result["is_up"],
            http_status=result["http_status"],
            response_time_ms=result["response_time_ms"],
            error_message=result["error_message"],
            ssl_valid=result["ssl_valid"],
            ssl_expiry_days=result["ssl_expiry_days"],
        )
        db.add(check)
        checked += 1

        # Check for state change and alert
        prev_state = _get_previous_state(db, disc.id)

        if not result["is_up"] and _count_recent_failures(db, disc.id) >= FAILURE_THRESHOLD - 1:
            # Site is down — check if we already have an open alert
            existing = db.query(Alert).filter(
                Alert.site_id == disc.id,
                Alert.type == "site_down",
                Alert.is_resolved == False,
            ).first()

            if not existing:
                server_name = disc.server.name if disc.server else "Unknown"
                create_and_dispatch_alert(
                    db,
                    alert_type="site_down",
                    severity="critical",
                    message=f"Website {domain} is DOWN. HTTP Status: {result['http_status'] or 'N/A'}. Error: {result['error_message'] or 'No response'}",
                    server_id=disc.server_id,
                    site_id=disc.id,
                    server_name=server_name,
                )

        elif result["is_up"] and prev_state is False:
            # Site recovered — resolve open alerts
            open_alerts = db.query(Alert).filter(
                Alert.site_id == disc.id,
                Alert.type == "site_down",
                Alert.is_resolved == False,
            ).all()
            for a in open_alerts:
                a.is_resolved = True
                a.resolved_at = datetime.utcnow()

        # SSL expiry warning
        if result["ssl_expiry_days"] is not None and result["ssl_expiry_days"] <= 14:
            existing_ssl = db.query(Alert).filter(
                Alert.site_id == disc.id,
                Alert.type == "ssl_expiring",
                Alert.is_resolved == False,
            ).first()
            if not existing_ssl:
                server_name = disc.server.name if disc.server else "Unknown"
                create_and_dispatch_alert(
                    db,
                    alert_type="ssl_expiring",
                    severity="warning",
                    message=f"SSL certificate for {domain} expires in {result['ssl_expiry_days']} days",
                    server_id=disc.server_id,
                    site_id=disc.id,
                    server_name=server_name,
                )

    try:
        db.commit()
    except Exception as e:
        logger.error(f"Uptime check commit error: {e}")
        db.rollback()

    logger.info(f"Uptime checks completed: {checked} sites checked")
    return checked


def uptime_check_job():
    """Scheduler job entry point for uptime monitoring."""
    db = next(get_db())
    try:
        run_uptime_checks(db)
    except Exception as e:
        logger.error(f"Uptime check job error: {e}")
    finally:
        db.close()
