def generate_recommendation(project):

    if (
        project.dns_points_here
        and project.web_config_active
    ):
        return {
            "action": "KEEP",
            "reason": "Live production project"
        }

    if (
        not project.dns_points_here
        and not project.web_config_active
        and project.risk_score >= 80
    ):
        return {
            "action": "DELETE",
            "reason": "High confidence duplicate"
        }

    if project.risk_score >= 50:
        return {
            "action": "ARCHIVE",
            "reason": "Inactive but should be reviewed"
        }

    return {
        "action": "REVIEW",
        "reason": "Needs manual verification"
    }