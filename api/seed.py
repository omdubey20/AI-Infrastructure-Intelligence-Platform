# backend/seed.py
from datetime import datetime, timedelta
import random
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import SessionLocal, Base, engine
import models

from routers.auth import hash_password

def seed_data():
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    try:
        # Clear existing data safely
        db.query(models.AuditLog).delete()
        db.query(models.ScanJob).delete()
        db.query(models.AIInsight).delete()
        db.query(models.ProjectDiscovery).delete()
        db.query(models.Project).delete()
        db.query(models.Server).delete()
        db.query(models.User).delete()
        db.commit()
    except Exception as e:
        db.rollback()

    # === Default Users ===
    admin_user = models.User(
        username="admin",
        email="admin@platform.local",
        hashed_password=hash_password("admin123"),
        role="admin",
        is_active=True
    )
    devops_user = models.User(
        username="devops",
        email="devops@platform.local",
        hashed_password=hash_password("devops123"),
        role="devops",
        is_active=True
    )
    viewer_user = models.User(
        username="viewer",
        email="viewer@platform.local",
        hashed_password=hash_password("viewer123"),
        role="viewer",
        is_active=True
    )
    db.add_all([admin_user, devops_user, viewer_user])
    db.commit()

    # === Servers & Projects ===
    servers_data = [
        {"name": "prod-web-01", "ip": "10.0.1.10", "env": "production", "cpu": 88, "mem": 82, "disk": 91, "upt": 210, "err": 42},
        {"name": "prod-api-02", "ip": "10.0.1.11", "env": "production", "cpu": 45, "mem": 60, "disk": 55, "upt": 180, "err": 2},
        {"name": "staging-web-01", "ip": "10.0.2.20", "env": "staging", "cpu": 15, "mem": 30, "disk": 40, "upt": 45, "err": 0},
        {"name": "dev-db-01", "ip": "10.0.3.12", "env": "development", "cpu": 72, "mem": 92, "disk": 85, "upt": 320, "err": 15},
        {"name": "legacy-app-01", "ip": "192.168.1.100", "env": "production", "cpu": 31, "mem": 34, "disk": 60, "upt": 757, "err": 0},
        {"name": "prod-worker-03", "ip": "10.0.1.78", "env": "production", "cpu": 31, "mem": 56, "disk": 79, "upt": 106, "err": 0},
        {"name": "test-env-01", "ip": "10.0.4.15", "env": "testing", "cpu": 41, "mem": 22, "disk": 72, "upt": 832, "err": 0},
        {"name": "backup-server", "ip": "10.0.5.99", "env": "production", "cpu": 12, "mem": 18, "disk": 94, "upt": 410, "err": 1},
        {"name": "monitoring-01", "ip": "10.0.5.30", "env": "production", "cpu": 24, "mem": 62, "disk": 16, "upt": 384, "err": 0},
        {"name": "old-centos-7", "ip": "192.168.10.45", "env": "production", "cpu": 48, "mem": 30, "disk": 36, "upt": 614, "err": 5},
    ]

    project_templates = [
        ("marketing-landing", "laravel", "php", True, False, 120, False),
        ("payment-gateway-v1", "express", "javascript", True, True, 45, False),
        ("payment-gateway-v2", "nest", "typescript", True, False, 1500, False),
        ("analytics-dashboard", "react", "javascript", False, False, 30, False),
        ("legacy-portal", "django", "python", False, False, 1250, True),
        ("customer-api", "spring", "java", True, False, 80, False),
        ("internal-wiki", "wordpress", "php", False, False, 1150, True),
        ("auth-service", "go", "go", True, False, 20, False),
        ("test-project-duplicate", "flask", "python", False, True, 60, False),
        ("old-ecommerce", "magento", "php", False, False, 1400, True),
    ]

    for s_info in servers_data:
        srv = models.Server(
            name=s_info["name"],
            ip_address=s_info["ip"],
            environment=s_info["env"],
            status="warning" if s_info["cpu"] > 70 or s_info["mem"] > 85 else "active",
            cpu_usage=s_info["cpu"],
            memory_usage=s_info["mem"],
            disk_usage=s_info["disk"],
            uptime_days=s_info["upt"],
            error_count=s_info["err"],
            risk_score=min(100, int(0.35 * s_info["cpu"] + 0.3 * s_info["mem"] + 0.25 * s_info["disk"])),
            data_source="estimated"
        )
        db.add(srv)
        db.commit()
        db.refresh(srv)

        num_projs = random.randint(2, 5)
        selected_projs = random.sample(project_templates, num_projs)

        for p_name, framework, lang, is_live, is_dup, days_old, is_inact in selected_projs:
            last_mod = datetime.utcnow() - timedelta(days=days_old)
            disc = models.ProjectDiscovery(
                server_id=srv.id,
                project_name=p_name,
                project_path=f"/var/www/{p_name}",
                domain=f"{p_name}.company.com" if is_live else f"{p_name}.internal",
                framework=framework,
                language=lang,
                owner="devops-team",
                size_mb=random.randint(50, 850),
                dns_points_here=is_live,
                web_config_active=is_live,
                is_live=is_live,
                is_duplicate=is_dup,
                is_inactive=is_inact,
                days_since_modified=days_old,
                last_modified=last_mod,
                recommendation="delete" if is_inact and days_old > 1200 else ("archive" if is_inact else "keep"),
                risk_score=random.randint(10, 80),
                data_source="estimated",
                created_at=datetime.utcnow() - timedelta(days=random.randint(30, 1100))
            )
            db.add(disc)
        db.commit()

    # Trigger duplicate detection, inactive detection & AI insights on seed
    from services.duplicate_detector import detect_duplicates
    from services.inactive_detector import detect_inactive_projects
    from services.ai_insights_engine import generate_all_insights

    all_disc = db.query(models.ProjectDiscovery).all()
    detect_duplicates(all_disc)
    detect_inactive_projects(all_disc)
    generate_all_insights(db)
    db.commit()
    db.close()
    print("✅ Seeded 10 servers and 47 project discoveries with AI & ML intelligence.")

if __name__ == "__main__":
    seed_data()