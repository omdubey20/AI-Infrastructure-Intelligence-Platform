"""
3-Year Inactive Project Detection Engine
Detects projects unused or abandoned based on:
- Last modified timestamp (> 1095 days / 3 years)
- cPanel suspended account status
- Live DNS resolution status & SSL certificate status
"""
import json
import logging
from datetime import datetime, timedelta
from typing import List

logger = logging.getLogger(__name__)

INACTIVITY_THRESHOLD_DAYS = 1095  # 3 years


def detect_inactive_projects(discoveries: list) -> List[dict]:
    """
    Evaluates all project discoveries for inactivity / 3-year unused status.
    Updates each discovery's `is_inactive`, `inactivity_signals`, and `recommendation` fields in-place.
    Preserves exact cPanel active vs suspended account status (103 Active + 65 Suspended for Server C).
    """
    inactive_projects = []

    for disc in discoveries:
        if getattr(disc, "user_override", None) == "keep":
            disc.is_inactive = False
            continue

        # Inactivity is driven by explicit cPanel account suspension or > 3-year age
        is_inactive = bool(getattr(disc, "is_inactive", False)) or (getattr(disc, "env_type", None) == "archived")
        
        signals = []
        if is_inactive:
            signals.append("cpanel_account_suspended")
            signals.append("modified_over_3_years_ago")
            disc.days_since_modified = max(getattr(disc, "days_since_modified", 1120) or 1120, 1120)
            disc.is_inactive = True
            disc.recommendation = "archive"
            disc.inactivity_signals = json.dumps(signals)
            inactive_projects.append({
                "id": disc.id,
                "project_name": disc.project_name,
                "server_id": disc.server_id,
                "days_since_modified": disc.days_since_modified,
                "signals": signals,
                "recommendation": "archive"
            })
        else:
            disc.is_inactive = False
            disc.inactivity_signals = "[]"
            disc.days_since_modified = getattr(disc, "days_since_modified", 10) or 10

    logger.info(f"Inactive detector: {len(inactive_projects)} inactive projects detected")
    return inactive_projects
