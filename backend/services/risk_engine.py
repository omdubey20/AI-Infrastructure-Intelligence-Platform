def calculate_server_risk(server):
    """
    Enterprise Risk Scoring Engine

    Score Range:
    0-30   = Healthy
    31-60  = Warning
    61-100 = Critical
    """

    risk = 0

    # CPU Risk
    if server.cpu_usage >= 90:
        risk += 25
    elif server.cpu_usage >= 75:
        risk += 15
    elif server.cpu_usage >= 60:
        risk += 5

    # Memory Risk
    if server.memory_usage >= 90:
        risk += 25
    elif server.memory_usage >= 75:
        risk += 15
    elif server.memory_usage >= 60:
        risk += 5

    # Disk Risk
    if server.disk_usage >= 90:
        risk += 30
    elif server.disk_usage >= 80:
        risk += 20
    elif server.disk_usage >= 70:
        risk += 10

    # Error Risk
    if server.error_count >= 50:
        risk += 25
    elif server.error_count >= 20:
        risk += 15
    elif server.error_count >= 5:
        risk += 5

    # Uptime Risk
    if server.uptime_days > 365:
        risk += 10
    elif server.uptime_days > 180:
        risk += 5

    return min(risk, 100)