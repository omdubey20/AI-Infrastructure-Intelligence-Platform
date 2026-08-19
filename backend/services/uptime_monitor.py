"""
Uptime Monitor Service
Concurrently checks all discovered project domains for HTTP availability every 60 seconds.
Records UptimeCheck records and creates/resolves alerts on state changes.
"""
import logging
import os
import socket
import ssl
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Optional

import requests
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models import ProjectDiscovery, UptimeCheck, Alert, Server
from services.notification_service import create_and_dispatch_alert

logger = logging.getLogger(__name__)

# Timeout for HTTP checks (fast 8s timeout for high throughput)
HTTP_TIMEOUT = 8


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
        result["ssl_valid"] = True

    except requests.exceptions.SSLError as e:
        result["error_message"] = f"SSL Error: {str(e)[:200]}"
        result["ssl_valid"] = False
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
                s.settimeout(4)
                s.connect((hostname, 443))
                cert = s.getpeercert()
                not_after = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
                result["ssl_expiry_days"] = (not_after - datetime.utcnow()).days
                result["ssl_valid"] = result["ssl_expiry_days"] > 0
        except Exception:
            pass

    return result


def _probe_worker(disc_info):
    disc_id, server_id, server_name, domain = disc_info
    url = f"https://{domain}" if not domain.startswith("http") else domain
    result = check_single_site(url)
    return disc_id, server_id, server_name, domain, url, result


def run_uptime_checks(db: Session):
    """Run concurrent uptime checks for all discovered projects with domains."""
    discoveries = db.query(ProjectDiscovery).options(
        joinedload(ProjectDiscovery.server)
    ).filter(
        ProjectDiscovery.domain.isnot(None),
        ProjectDiscovery.domain != "",
        ProjectDiscovery.is_live == True,
    ).all()

    if not discoveries:
        return 0

    items_to_check = [
        (d.id, d.server_id, d.server.name if d.server else "Unknown", d.domain.strip())
        for d in discoveries if d.domain and d.domain.strip()
    ]

    results = []
    with ThreadPoolExecutor(max_workers=25) as executor:
        futures = [executor.submit(_probe_worker, item) for item in items_to_check]
        for f in as_completed(futures):
            try:
                results.append(f.result())
            except Exception as e:
                logger.debug(f"Uptime probe worker error: {e}")

    checked = 0
    now = datetime.utcnow()
    for disc_id, server_id, server_name, domain, url, result in results:
        check = UptimeCheck(
            site_id=disc_id,
            server_id=server_id,
            url=url,
            is_up=result["is_up"],
            http_status=result["http_status"],
            response_time_ms=result["response_time_ms"],
            error_message=result["error_message"],
            ssl_valid=result["ssl_valid"],
            ssl_expiry_days=result["ssl_expiry_days"],
            checked_at=now,
        )
        db.add(check)
        checked += 1

        # Check for state change and alert
        if not result["is_up"]:
            existing = db.query(Alert).filter(
                Alert.site_id == disc_id,
                Alert.type == "site_down",
                Alert.is_resolved == False,
            ).first()

            if not existing:
                create_and_dispatch_alert(
                    db,
                    alert_type="site_down",
                    severity="critical",
                    message=f"Website {domain} is DOWN. HTTP Status: {result['http_status'] or 'N/A'}. Error: {result['error_message'] or 'No response'}",
                    server_id=server_id,
                    site_id=disc_id,
                    server_name=server_name,
                )

        else:
            # Site recovered — resolve open alerts
            open_alerts = db.query(Alert).filter(
                Alert.site_id == disc_id,
                Alert.type == "site_down",
                Alert.is_resolved == False,
            ).all()
            for a in open_alerts:
                a.is_resolved = True
                a.resolved_at = now

        # SSL expiry warning
        if result["ssl_expiry_days"] is not None and result["ssl_expiry_days"] <= 14:
            existing_ssl = db.query(Alert).filter(
                Alert.site_id == disc_id,
                Alert.type == "ssl_expiring",
                Alert.is_resolved == False,
            ).first()
            if not existing_ssl:
                create_and_dispatch_alert(
                    db,
                    alert_type="ssl_expiring",
                    severity="warning",
                    message=f"SSL certificate for {domain} expires in {result['ssl_expiry_days']} days",
                    server_id=server_id,
                    site_id=disc_id,
                    server_name=server_name,
                )

    try:
        db.commit()
    except Exception as e:
        logger.error(f"Uptime check commit error: {e}")
        db.rollback()

    logger.info(f"Concurrent uptime checks completed: {checked} sites checked in parallel")
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
