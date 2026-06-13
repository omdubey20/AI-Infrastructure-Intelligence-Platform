from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import models
from database import get_db
from services.duplicate_engine import analyze_duplicates

router = APIRouter(
    prefix="/cleanup",
    tags=["Cleanup"]
)


@router.get("/report")
def cleanup_report(db: Session = Depends(get_db)):

    discoveries = db.query(models.ProjectDiscovery).all()

    duplicate_analysis = analyze_duplicates(discoveries)

    analysis_map = {
        item["id"]: item
        for item in duplicate_analysis
    }

    projects = []

    delete_count = 0
    archive_count = 0
    keep_count = 0

    for item in discoveries:

        analysis = analysis_map[item.id]

        recommendation = analysis["recommendation"]
        duplicate_confidence = analysis["duplicate_confidence"]
        reason = analysis["reason"]

        if recommendation == "DELETE":
            delete_count += 1

        elif recommendation == "ARCHIVE":
            archive_count += 1

        else:
            keep_count += 1

        server_name = "Unknown"

        if item.server:
            server_name = item.server.name

        projects.append(
            {
                "projectid": item.id,
                "projectname": item.project_name,
                "servername": server_name,
                "riskscore": item.risk_score,
                "recommendedaction": recommendation,
                "duplicateconfidence": duplicate_confidence,
                "reason": reason,
                "dns_points_here": item.dns_points_here,
                "web_config_active": item.web_config_active
            }
        )

    return {
        "totalprojects": len(discoveries),
        "deletecandidates": delete_count,
        "archivecandidates": archive_count,
        "keepcount": keep_count,
        "projects": projects
    }


@router.post("/approve/{project_id}")
def approve_cleanup(
    project_id: int,
    action: str,
    db: Session = Depends(get_db)
):

    project = (
        db.query(models.ProjectDiscovery)
        .filter(
            models.ProjectDiscovery.id == project_id
        )
        .first()
    )

    if not project:
        return {
            "success": False,
            "message": "Project not found"
        }

    return {
        "success": True,
        "project_id": project_id,
        "action": action,
        "message": f"{action.upper()} approved"
    }