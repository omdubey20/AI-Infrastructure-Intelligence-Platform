import socket

def check_dns_live(domain):
    """Check if domain resolves to an IP"""
    try:
        ip = socket.gethostbyname(domain)
        return True, ip
    except Exception:
        return False, None

def check_project_health(domain, path):
    """
    Check real project health:
    - DNS: does domain resolve?
    - Web config: is path a real web directory?
    - Risk: based on DNS + config status
    """
    dns_live, ip = check_dns_live(domain)
    
    # Web config active if path looks like a real web path
    web_active = bool(path and ("public_html" in path or "www" in path or "html" in path))
    
    # Risk score based on health
    if dns_live and web_active:
        risk = 15  # healthy
    elif dns_live and not web_active:
        risk = 45  # DNS works but no web config
    elif not dns_live and web_active:
        risk = 60  # has config but no DNS
    else:
        risk = 75  # no DNS, no config
    
    return dns_live, web_active, risk
