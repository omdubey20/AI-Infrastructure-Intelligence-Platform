"""
Risk Scoring Engine
Calculates risk scores using ML model when available, falls back to deterministic rules.
Supports data source weighting: agent > ssh > whm > estimated.
Applies data freshness penalty when metrics are stale.
"""
import os
import pickle
from datetime import datetime, timedelta

import numpy as np


_model = None
_model_path = os.path.join(os.path.dirname(__file__), "risk_model.pkl")


def _load_model():
    global _model
    try:
        if os.path.exists(_model_path):
            with open(_model_path, "rb") as f:
                _model = pickle.load(f)
    except Exception:
        _model = None


_load_model()


def _clamp_percent(value, default=0):
    try:
        value = int(float(value))
        return max(0, min(100, value))
    except Exception:
        return default


def _clamp_non_negative(value, default=0):
    try:
        value = int(float(value))
        return max(0, value)
    except Exception:
        return default


# Data source confidence multipliers (higher = more trusted)
SOURCE_CONFIDENCE = {
    "agent": 1.0,
    "ssh": 0.95,
    "whm": 0.85,
    "whm_estimated": 0.80,
    "estimated": 0.70,
}


def _get_metrics(server):
    cpu = _clamp_percent(getattr(server, "cpu_usage", 0), 0)
    memory = _clamp_percent(getattr(server, "memory_usage", 0), 0)
    disk = _clamp_percent(getattr(server, "disk_usage", 0), 0)
    uptime = _clamp_non_negative(getattr(server, "uptime_days", 0), 0)
    errors = _clamp_non_negative(getattr(server, "error_count", 0), 0)
    source = getattr(server, "data_source", "estimated") or "estimated"
    return cpu, memory, disk, uptime, errors, source


def _get_freshness_penalty(server) -> int:
    """
    Penalize risk score when data is stale.
    - No penalty if last scan < 10 min ago
    - +5 if 10-30 min
    - +10 if 30-60 min
    - +15 if > 1 hour
    """
    last_scan = getattr(server, "last_scanned_at", None)
    agent_seen = getattr(server, "agent_last_seen", None)

    # Use the most recent of the two timestamps
    latest = None
    if last_scan and agent_seen:
        latest = max(last_scan, agent_seen)
    elif last_scan:
        latest = last_scan
    elif agent_seen:
        latest = agent_seen

    if not latest:
        return 10  # No data at all = moderate penalty

    age = datetime.utcnow() - latest
    if age < timedelta(minutes=10):
        return 0
    elif age < timedelta(minutes=30):
        return 5
    elif age < timedelta(hours=1):
        return 10
    else:
        return 15


def calculate_server_risk(server):
    """
    Risk scoring engine.

    Uses the trained model when available.
    Falls back to deterministic rule-based scoring.
    Applies data source confidence weighting and freshness penalty.

    Score Range:
        0-30   = Healthy
        31-60  = Warning
        61-100 = Critical
    """
    cpu, memory, disk, uptime, errors, source = _get_metrics(server)
    confidence = SOURCE_CONFIDENCE.get(source, 0.70)

    if _model is not None:
        try:
            features = np.array([[cpu, memory, disk, uptime, errors]], dtype=float)
            score = int(_model.predict(features)[0])
            score = max(0, min(100, score))

            # Apply confidence scaling for non-agent sources
            if confidence < 1.0:
                score = min(100, int(score * confidence))

            # Add freshness penalty
            score = min(100, score + _get_freshness_penalty(server))

            return score
        except Exception:
            pass

    risk = 0

    if cpu >= 90:
        risk += 30
    elif cpu >= 75:
        risk += 20
    elif cpu >= 60:
        risk += 10

    if memory >= 90:
        risk += 25
    elif memory >= 75:
        risk += 15
    elif memory >= 60:
        risk += 8

    if disk >= 90:
        risk += 30
    elif disk >= 80:
        risk += 20
    elif disk >= 70:
        risk += 10

    if errors >= 50:
        risk += 10
    elif errors >= 20:
        risk += 6
    elif errors >= 5:
        risk += 3

    if uptime > 365:
        risk += 5
    elif uptime > 180:
        risk += 3

    # Apply confidence for non-agent/ssh sources
    if confidence < 0.95:
        if cpu >= 85:
            risk -= 4
        if memory >= 85:
            risk -= 4
        risk = max(risk, disk)

    # Freshness penalty
    risk += _get_freshness_penalty(server)

    return max(0, min(100, risk))


def get_data_source(server):
    value = getattr(server, "data_source", None)
    if value in {"agent", "ssh", "whm", "whm_estimated", "estimated"}:
        return value
    return "estimated"