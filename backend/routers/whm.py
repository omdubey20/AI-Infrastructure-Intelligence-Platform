from fastapi import APIRouter, Depends
from routers.auth import get_current_user
from services.whm_service import get_full_server_report, get_server_load, get_whm_accounts

router = APIRouter(prefix="/whm", tags=["WHM"])


@router.get("/report")
def whm_report(current_user=Depends(get_current_user)):
    return get_full_server_report()


@router.get("/health")
def whm_health(current_user=Depends(get_current_user)):
    return get_server_load()


@router.get("/accounts")
def whm_accounts(current_user=Depends(get_current_user)):
    return get_whm_accounts()
