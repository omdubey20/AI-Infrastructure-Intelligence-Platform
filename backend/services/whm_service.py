"""
Expanded WHM/cPanel Service
Fetches accounts, domains, disk, SSL, load, and per-account metadata.
"""
import os
import logging
import warnings
import requests
from dotenv import load_dotenv

warnings.filterwarnings("ignore")
load_dotenv()
logger = logging.getLogger(__name__)


def _whm_get(host: str, token: str, port: int, endpoint: str, params: dict = None) -> dict:
    """
    Make authenticated WHM API GET request with enterprise resilience.
    Uses browser-mimicking headers, session persistence, and cPHulk/cPanel challenge handling.
    """
    url = f"https://{host}:{port}/json-api/{endpoint}"
    headers = {
        "Authorization": f"whm root:{token}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
    }
    
    session = requests.Session()
    session.verify = False

    try:
        r = session.get(url, headers=headers, params=params or {}, timeout=15)
        if r.status_code == 200:
            try:
                return r.json()
            except Exception:
                # If WHM returned HTML security challenge/cPHulk redirect, attempt API v1 explicit JSON endpoint
                alt_url = f"https://{host}:{port}/json-api/{endpoint}?api.version=1"
                r2 = session.get(alt_url, headers=headers, timeout=15)
                return r2.json()
        elif r.status_code in (403, 401, 429):
            try:
                err_data = r.json()
                msg = err_data.get("message") or err_data.get("metadata", {}).get("reason")
                if msg:
                    logger.warning(f"WHM Security Block ({r.status_code}) on {host}: {msg}")
                    return {"error": msg, "status_code": r.status_code, "is_security_block": True}
            except Exception:
                pass
            return {"error": f"HTTP {r.status_code} Access Denied (Imunify360 / cPHulk Protection)", "status_code": r.status_code, "is_security_block": True}
        return {}
    except Exception as e:
        logger.warning(f"WHM API error {endpoint} on {host}: {e}")
        return {}


def get_whm_accounts(host: str = None, token: str = None, port: int = 2087) -> list:
    """Get WHM accounts using provided host/token or environment defaults."""
    h = host or os.getenv("WHM_HOST")
    t = token or os.getenv("WHM_TOKEN")
    p = port or int(os.getenv("WHM_PORT", "2087"))
    if not (h and t):
        return []
    return get_whm_accounts_for_server(h, t, p)


def get_whm_accounts_for_server(host: str, token: str, port: int = 2087) -> list:
    """List all cPanel accounts on a WHM server."""
    data = _whm_get(host, token, port, "listaccts", {"api.version": "1"})
    return data.get("data", {}).get("acct", [])


def get_server_load(host: str = None, token: str = None, port: int = 2087) -> dict:
    """Get server load averages from WHM systemloadavg API."""
    h = host or os.getenv("WHM_HOST")
    t = token or os.getenv("WHM_TOKEN")
    p = port or int(os.getenv("WHM_PORT", "2087"))
    if not (h and t):
        return {"load_1": 0, "load_5": 0, "load_15": 0}
    data = _whm_get(h, t, p, "systemloadavg", {"api.version": "1"})
    d = data.get("data", {})
    return {
        "load_1": float(d.get("one", 0)),
        "load_5": float(d.get("five", 0)),
        "load_15": float(d.get("fifteen", 0)),
    }


def get_server_disk(host: str, token: str, port: int = 2087) -> int:
    """Get aggregate disk usage percentage from all WHM accounts."""
    accts = get_whm_accounts_for_server(host, token, port)
    if not accts:
        return 0
    total_used = 0
    total_limit = 0
    for acc in accts:
        disk_str = str(acc.get("diskused", "0")).replace("M", "").replace("G", "000").replace("K", "")
        limit_str = str(acc.get("disklimit", "0")).replace("M", "").replace("G", "000").replace("K", "")
        try:
            total_used += float(disk_str)
        except Exception:
            pass
        try:
            if limit_str not in ("0", "unlimited", ""):
                total_limit += float(limit_str)
        except Exception:
            pass
    if total_limit > 0:
        return min(95, int((total_used / total_limit) * 100))
    return 35  # Default estimate when no limit set


def get_account_domains_with_creds(host: str, token: str, port: int, username: str) -> list:
    """Get all domains for a cPanel account (main + addon, skip system subdomains)."""
    url = (f"https://{host}:{port}/json-api/cpanel"
           f"?cpanel_jsonapi_user={username}"
           f"&cpanel_jsonapi_module=DomainInfo"
           f"&cpanel_jsonapi_func=domains_data"
           f"&cpanel_jsonapi_apiversion=3")
    headers = {"Authorization": f"whm root:{token}"}
    try:
        r = requests.get(url, headers=headers, verify=False, timeout=15)
        data = r.json().get("result", {}).get("data", {})
        domains = []

        main = data.get("main_domain", {})
        if main and main.get("domain"):
            domains.append({
                "name": main.get("domain"),
                "path": main.get("documentroot", f"/home/{username}/public_html"),
                "type": "main",
                "ip": main.get("ip"),
                "php": main.get("phpversion"),
            })

        for addon in data.get("addon_domains", []):
            if addon.get("domain"):
                domains.append({
                    "name": addon.get("domain"),
                    "path": addon.get("documentroot", f"/home/{username}/public_html"),
                    "type": "addon",
                    "ip": addon.get("ip"),
                    "php": addon.get("phpversion"),
                })

        return domains
    except Exception as e:
        logger.warning(f"Domain fetch failed for {username}: {e}")
        return []


def get_whm_ssl_certs(host: str, token: str, port: int = 2087) -> list:
    """Get all SSL certificates and their expiry from WHM."""
    accts = get_whm_accounts_for_server(host, token, port)
    certs = []
    for acc in accts:
        username = acc.get("user", "")
        domain = acc.get("domain", "")
        if not domain:
            continue
        from services.server_scanner import check_ssl
        has_ssl, expiry_days = check_ssl(domain)
        certs.append({
            "username": username,
            "domain": domain,
            "has_ssl": has_ssl,
            "expiry_days": expiry_days,
        })
    return certs


def get_full_server_report(host: str = None, token: str = None, port: int = 2087) -> dict:
    """Get complete WHM server report."""
    h = host or os.getenv("WHM_HOST")
    t = token or os.getenv("WHM_TOKEN")
    p = port or int(os.getenv("WHM_PORT", "2087"))

    accounts = get_whm_accounts_for_server(h, t, p)
    load = get_server_load(h, t, p)
    return {
        "server": h,
        "load": load,
        "account_count": len(accounts),
        "accounts": accounts,
    }
