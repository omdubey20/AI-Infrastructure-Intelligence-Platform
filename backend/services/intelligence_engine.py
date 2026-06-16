# backend/services/intelligence_engine.py
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import models
import random  # For demo scoring - replace with real logic later

def calculate_risk_score(discovery: models.ProjectDiscovery) -> dict:
    """AI-style risk scoring"""
    age_days = (datetime.utcnow() - discovery.created_at).days
    
    base_risk = 20
    if age_days > 1095:  # 3+ years
        base_risk += 50
    elif age_days > 365:
        base_risk += 25
    
    if not discovery.dns_points_here:
        base_risk += 15
    if not discovery.web_config_active:
        base_risk += 20
    
    # Simulate anomaly / growth risk
    anomaly_factor = random.randint(0, 30)
    
    final_score = min(95, base_risk + anomaly_factor)
    
    if final_score >= 75:
        recommendation = "DELETE"
        confidence = 85
        reason = "Stale (>3 years) + no active DNS/config"
    elif final_score >= 50:
        recommendation = "ARCHIVE"
        confidence = 70
        reason = "Low activity + duplicate candidate"
    else:
        recommendation = "KEEP"
        confidence = 90
        reason = "Active configuration detected"
    
    return {
        "risk_score": final_score,
        "recommendation": recommendation,
        "confidence": confidence,
        "reason": reason,
        "age_days": age_days
    }

def analyze_all_discoveries(db: Session):
    discoveries = db.query(models.ProjectDiscovery).all()
    results = []
    
    for disc in discoveries:
        intel = calculate_risk_score(disc)
        results.append({
            "id": disc.id,
            "project_name": disc.project_name,
            "server_name": disc.server.name if disc.server else "Unknown",
            **intel
        })
    
    return results
