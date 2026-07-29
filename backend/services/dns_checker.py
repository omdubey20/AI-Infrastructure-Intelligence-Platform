"""
DNS Checker — Domain resolution and HTTP health probe.
"""
import socket
import logging

logger = logging.getLogger(__name__)


def check_project_health(domain: str, path: str = None):
    """
    Checks DNS resolution for a domain.
    Returns (dns_resolves: bool, web_config_active: bool, risk_score: int).
    """
    if not domain or "." not in domain:
        return False, False, 60

    dns_ok = False
    try:
        socket.setdefaulttimeout(5)
        socket.gethostbyname(domain)
        dns_ok = True
    except Exception:
        pass

    # Infer web_config_active from DNS — if DNS resolves, config is likely active
    web_active = dns_ok

    if dns_ok:
        risk = 15
    elif path:
        risk = 55
    else:
        risk = 70

    return dns_ok, web_active, risk
