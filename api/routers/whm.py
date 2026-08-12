"""
WHM / cPanel Router
Exposes WHM server report, load averages, accounts listing, SSL certs.
"""
import os
from fastapi import APIRouter, Depends
from routers.auth import get_current_user
from services.whm_service import (
    get_full_server_report,
    get_server_load,
    get_whm_accounts,
    get_whm_ssl_certs,
)

router = APIRouter(prefix="/whm", tags=["WHM"])


@router.get("/report")
def whm_report(current_user=Depends(get_current_user)):
    """Full WHM server report with accounts and load average."""
    return get_full_server_report()


@router.get("/health")
def whm_health(current_user=Depends(get_current_user)):
    """WHM system load averages (1, 5, 15 min)."""
    return get_server_load()


@router.get("/accounts")
def whm_accounts(current_user=Depends(get_current_user)):
    """List all cPanel accounts from configured WHM server."""
    accounts = get_whm_accounts()
    return {"count": len(accounts), "accounts": accounts}


@router.get("/ssl")
def whm_ssl(current_user=Depends(get_current_user)):
    """List all SSL cert expiry dates for WHM-hosted domains."""
    host = os.getenv("WHM_HOST")
    token = os.getenv("WHM_TOKEN")
    port = int(os.getenv("WHM_PORT", "2087"))
    if not (host and token):
        return {"error": "WHM credentials not configured", "certs": []}
    certs = get_whm_ssl_certs(host, token, port)
    return {"count": len(certs), "certs": certs}
