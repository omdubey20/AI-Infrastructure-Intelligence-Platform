# backend/seed.py
from datetime import datetime, timedelta
import random
from sqlalchemy.orm import Session
from database import SessionLocal
import models

def seed_data():
    db: Session = SessionLocal()
    
    # Clear existing data (careful in production!)
    db.query(models.ProjectDiscovery).delete()
    db.query(models.Project).delete()
    db.query(models.Server).delete()
    db.commit()

    # === 10 Realistic Servers ===
    servers_data = [
        {"name": "prod-web-01", "ip": "10.0.1.45", "env": "production", "status": "active", "desc": "Primary web cluster"},
        {"name": "prod-api-02", "ip": "10.0.1.46", "env": "production", "status": "active", "desc": "API gateway"},
        {"name": "staging-web-01", "ip": "10.0.2.10", "env": "staging", "status": "active"},
        {"name": "dev-db-01", "ip": "10.0.3.22", "env": "development", "status": "active"},
        {"name": "legacy-app-01", "ip": "192.168.1.100", "env": "production", "status": "maintenance", "desc": "Old PHP monolith"},
        {"name": "prod-worker-03", "ip": "10.0.1.78", "env": "production", "status": "active"},
        {"name": "test-env-01", "ip": "10.0.4.15", "env": "testing", "status": "active"},
        {"name": "backup-server", "ip": "10.0.1.200", "env": "production", "status": "active"},
        {"name": "monitoring-01", "ip": "10.0.5.30", "env": "production", "status": "active"},
        {"name": "old-centos-7", "ip": "192.168.10.45", "env": "production", "status": "warning", "desc": "End-of-life OS"},
    ]

    servers = []
    for s in servers_data:
        server = models.Server(
            name=s["name"],
            ip_address=s["ip"],
            environment=s["env"],
            status=s.get("status", "active"),
            description=s.get("desc"),
            cpu_usage=random.randint(10, 85),
            memory_usage=random.randint(20, 92),
            disk_usage=random.randint(15, 88),
            error_count=random.randint(0, 12),
            uptime_days=random.randint(30, 890),
            risk_score=random.randint(10, 75)
        )
        db.add(server)
        db.commit()
        db.refresh(server)
        servers.append(server)

    # === 47 Project Discoveries ===
    project_names = [
        "frontend-app", "backend-api", "admin-panel", "user-service", "payment-gateway",
        "analytics-dashboard", "notification-service", "file-storage", "auth-service",
        "legacy-crm", "old-ecommerce", "test-project", "staging-v2", "backup-copy",
        "archive-2022", "mobile-app", "docs-site", "internal-tools", "monitoring-ui",
        "old-wordpress", "php-monolith", "react-dashboard", "node-microservice", "docker-test",
        "unused-project", "temp-experiment", "client-portal", "invoice-system", "hr-portal",
        "duplicate-frontend", "frontend-v2", "api-v1", "api-v2", "webhook-handler",
        "report-generator", "data-pipeline", "ml-model-serving", "cache-layer", "queue-worker",
        "old-laravel", "symfony-app", "static-site", "marketing-landing", "blog-engine"
    ]

    discoveries = []
    for i in range(47):
        server = random.choice(servers)
        name = random.choice(project_names)
        if i % 5 == 0:  # create some obvious duplicates
            name += "-duplicate"

        disc = models.ProjectDiscovery(
            server_id=server.id,
            project_name=name,
            project_path=f"/var/www/{name.replace('-', '_')}",
            size_mb=random.randint(5, 850),
            domain=f"{name.lower().replace(' ', '')}.example.com" if random.random() > 0.4 else None,
            dns_points_here=random.choice([True, False]),
            web_config_active=random.choice([True, False]),
            risk_score=random.randint(10, 95),
            created_at=datetime.utcnow() - timedelta(days=random.randint(30, 1100))
        )
        db.add(disc)
        discoveries.append(disc)

    db.commit()
    print(f"✅ Seeded {len(servers)} servers and {len(discoveries)} project discoveries")
    db.close()

if __name__ == "__main__":
    seed_data()