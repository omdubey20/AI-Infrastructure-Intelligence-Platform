import os
import pickle

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


def _get_metrics(server):
    cpu = _clamp_percent(getattr(server, "cpu_usage", 0), 0)
    memory = _clamp_percent(getattr(server, "memory_usage", 0), 0)
    disk = _clamp_percent(getattr(server, "disk_usage", 0), 0)
    uptime = _clamp_non_negative(getattr(server, "uptime_days", 0), 0)
    errors = _clamp_non_negative(getattr(server, "error_count", 0), 0)
    source = getattr(server, "data_source", "estimated") or "estimated"
    return cpu, memory, disk, uptime, errors, source


def calculate_server_risk(server):
    """
    Risk scoring engine.

    Uses the trained model when available.
    Falls back to deterministic rule-based scoring.

    Score Range:
        0-30   = Healthy
        31-60  = Warning
        61-100 = Critical
    """
    cpu, memory, disk, uptime, errors, source = _get_metrics(server)

    if _model is not None:
        try:
            features = np.array([[cpu, memory, disk, uptime, errors]], dtype=float)
            score = int(_model.predict(features)[0])
            score = max(0, min(100, score))

            if source != "ssh":
                score = min(100, int(score * 0.9))

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

    if source != "ssh":
        if cpu >= 85:
            risk -= 4
        if memory >= 85:
            risk -= 4
        risk = max(risk, disk)

    return max(0, min(100, risk))


def get_data_source(server):
    value = getattr(server, "data_source", None)
    if value in {"ssh", "whm_estimated", "estimated"}:
        return value
    return "estimated"