"""
AI Insights & Recommendations Router
Exposes AI recommendations, server-specific insights, and security alerts.
"""
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import AIInsight
from routers.auth import get_current_user
from services.ai_insights_engine import generate_all_insights

router = APIRouter(prefix="/ai", tags=["AI Insights"])


@router.get("/insights")
def get_insights(
    server_id: Optional[int] = None,
    category: Optional[str] = None,
    severity: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    query = db.query(AIInsight)
    if server_id:
        query = query.filter(AIInsight.server_id == server_id)
    if category:
        query = query.filter(AIInsight.category == category)
    if severity:
        query = query.filter(AIInsight.severity == severity)

    insights = query.all()
    if not insights and not server_id and not category and not severity:
        # Refresh insights dynamically if empty
        insights = generate_all_insights(db)

    return [
        {
            "id": i.id,
            "server_id": i.server_id,
            "project_id": i.project_id,
            "category": i.category,
            "severity": i.severity,
            "title": i.title,
            "description": i.description,
            "recommendation": i.recommendation,
            "is_resolved": i.is_resolved,
            "created_at": i.created_at.isoformat() if i.created_at else None
        }
        for i in insights
    ]


@router.post("/refresh")
def refresh_ai(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    insights = generate_all_insights(db)
    return {"message": "AI insights refreshed successfully", "count": len(insights)}
