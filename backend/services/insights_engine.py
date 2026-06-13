def generate_server_insights(server):
    insights = []

    if server.cpu_usage >= 80:
        insights.append(
            "High CPU usage detected"
        )

    if server.memory_usage >= 75:
        insights.append(
            "Memory pressure increasing"
        )

    if server.disk_usage >= 85:
        insights.append(
            "Disk space running low"
        )

    if server.error_count >= 10:
        insights.append(
            "Frequent errors detected"
        )

    if server.uptime_days >= 180:
        insights.append(
            "Long uptime. Consider maintenance window"
        )

    if len(insights) == 0:
        insights.append(
            "Infrastructure healthy"
        )

    return insights