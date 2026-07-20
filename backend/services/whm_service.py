import os
import requests
import warnings
from dotenv import load_dotenv

warnings.filterwarnings("ignore")
load_dotenv()

WHM_HOST = os.getenv("WHM_HOST")
WHM_TOKEN = os.getenv("WHM_TOKEN")
WHM_PORT = os.getenv("WHM_PORT", "2087")
BASE_URL = f"https://{WHM_HOST}:{WHM_PORT}/json-api"
HEADERS = {"Authorization": f"whm root:{WHM_TOKEN}"}


def get_whm_accounts():
    try:
        r = requests.get(f"{BASE_URL}/listaccts?api.version=1",
                        headers=HEADERS, verify=False, timeout=10)
        return r.json().get("data", {}).get("acct", [])
    except Exception as e:
        return []


def get_server_load():
    try:
        r = requests.get(f"{BASE_URL}/systemloadavg?api.version=1",
                        headers=HEADERS, verify=False, timeout=10)
        data = r.json().get("data", {})
        return {
            "load_1": float(data.get("one", 0)),
            "load_5": float(data.get("five", 0)),
            "load_15": float(data.get("fifteen", 0)),
        }
    except Exception:
        return {"load_1": 0, "load_5": 0, "load_15": 0}


def get_account_domains(username):
    try:
        url = (f"{BASE_URL}/cpanel?cpanel_jsonapi_user={username}"
               f"&cpanel_jsonapi_module=DomainInfo"
               f"&cpanel_jsonapi_func=domains_data"
               f"&cpanel_jsonapi_apiversion=3")
        r = requests.get(url, headers=HEADERS, verify=False, timeout=10)
        data = r.json().get("result", {}).get("data", {})
        domains = []
        main = data.get("main_domain", {})
        if main:
            domains.append({
                "name": main.get("domain"),
                "type": "main",
                "path": main.get("documentroot"),
                "ip": main.get("ip"),
                "php": main.get("phpversion"),
                "status": main.get("status"),
            })
        for sub in data.get("sub_domains", []):
            domains.append({
                "name": sub.get("domain"),
                "type": "subdomain",
                "path": sub.get("documentroot"),
                "ip": sub.get("ip"),
                "php": sub.get("phpversion"),
                "status": sub.get("status"),
            })
        for addon in data.get("addon_domains", []):
            domains.append({
                "name": addon.get("domain"),
                "type": "addon",
                "path": addon.get("documentroot"),
                "ip": addon.get("ip"),
                "php": addon.get("phpversion"),
                "status": addon.get("status"),
            })
        return domains
    except Exception:
        return []


def get_full_server_report():
    accounts = get_whm_accounts()
    load = get_server_load()
    result = {
        "server": WHM_HOST,
        "ip": "212.48.85.72",
        "load": load,
        "accounts": []
    }
    for acc in accounts:
        username = acc.get("user")
        domains = get_account_domains(username)
        result["accounts"].append({
            "username": username,
            "domain": acc.get("domain"),
            "disk_used": acc.get("diskused"),
            "disk_limit": acc.get("disklimit"),
            "suspended": acc.get("suspended"),
            "email": acc.get("email"),
            "php": acc.get("phpversion", "unknown"),
            "domains": domains,
        })
    return result
