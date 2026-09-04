"""
Enterprise Test Suite for AI Infrastructure Intelligence Platform
Tests: Auth, Servers, Projects, Uptime Monitoring, Alerts, Malware Scanning,
       Agent Telemetry, Teams/Email Notifications, Risk Engine, Duplicate Detection,
       Credential Encryption, and ML Pipeline.
"""
import os
import sys
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# Ensure backend is on path and test DB URL is set BEFORE importing database or main
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["DATABASE_URL"] = "sqlite:///./test_infra.db"
os.environ["SECRET_KEY"] = "test-secret-key-for-unit-testing-32-chars-long"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db, engine
from main import app
import models

# In-memory/local SQLite session for isolation
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True, scope="session")
def setup_database():
    """Create all tables before tests, seed test user, drop after."""
    Base.metadata.create_all(bind=engine)
    db = TestSession()
    try:
        from routers.auth import hash_password
        existing = db.query(models.User).filter(models.User.username == "testadmin").first()
        if not existing:
            user = models.User(
                username="testadmin",
                email="admin@test.com",
                hashed_password=hash_password("testpassword123"),
                is_active=True,
                role="admin"
            )
            db.add(user)
            db.commit()
    finally:
        db.close()
    yield
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("./test_infra.db"):
        try:
            os.remove("./test_infra.db")
        except Exception:
            pass


_cached_token = None

def get_auth_token() -> str:
    """Helper: login and return bearer token."""
    global _cached_token
    if _cached_token:
        return _cached_token
    resp = client.post(
        "/auth/login",
        data={"username": "testadmin", "password": "testpassword123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    _cached_token = resp.json()["access_token"]
    return _cached_token


def auth_headers() -> dict:
    return {"Authorization": f"Bearer {get_auth_token()}"}


# ============================================================
# 1: HEALTH & ROOT
# ============================================================

class TestHealthEndpoints:
    def test_root_returns_200(self):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "running"
        assert "version" in data

    def test_health_returns_200(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "database" in data


# ============================================================
# 2: AUTHENTICATION
# ============================================================

class TestAuth:
    def test_login_valid_credentials(self):
        resp = client.post(
            "/auth/login",
            data={"username": "testadmin", "password": "testpassword123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_password(self):
        resp = client.post(
            "/auth/login",
            data={"username": "testadmin", "password": "wrongpassword"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert resp.status_code == 401

    def test_me_with_valid_token(self):
        resp = client.get("/auth/me", headers=auth_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "testadmin"
        assert data["role"] == "admin"

    def test_me_without_token_returns_401(self):
        resp = client.get("/auth/me")
        assert resp.status_code in (401, 403)


# ============================================================
# 3: SERVERS CRUD & METRICS
# ============================================================

class TestServersAPI:
    def test_list_servers_with_auth(self):
        resp = client.get("/servers/", headers=auth_headers())
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_and_get_server(self):
        resp = client.post("/servers/", json={
            "name": "Production VPS A",
            "ip_address": "192.168.1.100",
            "environment": "production",
            "status": "active",
            "ssh_username": "root",
            "ssh_port": 22,
        }, headers=auth_headers())
        assert resp.status_code in (200, 201)
        data = resp.json()
        server_id = data["id"]
        assert data["ip_address"] == "192.168.1.100"

        # Fetch detail
        detail_resp = client.get(f"/servers/{server_id}", headers=auth_headers())
        assert detail_resp.status_code == 200
        assert detail_resp.json()["name"] == "Production VPS A"


# ============================================================
# 4: PROJECTS API
# ============================================================

class TestProjectsAPI:
    def test_list_projects_with_auth(self):
        resp = client.get("/projects/", headers=auth_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "projects" in data
        assert "total" in data


# ============================================================
# 5: AGENT API & TELEMETRY
# ============================================================

class TestAgentAPI:
    def test_install_script_endpoint(self):
        resp = client.get("/agent/install.sh")
        assert resp.status_code == 200
        assert "#!/bin/bash" in resp.text
        assert "Infra Intel Agent" in resp.text

    def test_generate_agent_key_and_report(self):
        # 1. Create a server
        srv_resp = client.post("/servers/", json={
            "name": "Agent Monitored Server",
            "ip_address": "10.10.10.50",
            "environment": "production",
        }, headers=auth_headers())
        server_id = srv_resp.json()["id"]

        # 2. Generate key
        key_resp = client.post(f"/agent/generate-key/{server_id}", headers=auth_headers())
        assert key_resp.status_code == 200
        api_key = key_resp.json()["api_key"]
        assert api_key.startswith("infra_")

        # 3. Send agent report telemetry
        report_payload = {
            "api_key": api_key,
            "cpu_usage": 42,
            "memory_usage": 65,
            "disk_usage": 55,
            "load_avg_1": 1.25,
            "load_avg_5": 1.10,
            "load_avg_15": 0.95,
            "uptime_days": 120,
            "error_count": 2,
            "ram_total_gb": 16.0,
            "hostname": "vps-agent-01",
            "os_name": "Ubuntu 22.04 LTS",
            "kernel": "5.15.0-generic"
        }
        report_resp = client.post("/agent/report", json=report_payload)
        assert report_resp.status_code == 200
        assert report_resp.json()["status"] == "ok"

        # 4. Verify server updated with real agent metrics
        detail_resp = client.get(f"/servers/{server_id}", headers=auth_headers())
        assert detail_resp.status_code == 200
        srv_data = detail_resp.json()
        assert srv_data["cpu_usage"] == 42
        assert srv_data["memory_usage"] == 65
        assert srv_data["data_source"] == "agent"

    def test_agent_status_list(self):
        resp = client.get("/agent/status", headers=auth_headers())
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ============================================================
# 6: UPTIME MONITORING API
# ============================================================

class TestUptimeMonitoringAPI:
    def test_monitoring_status(self):
        resp = client.get("/monitoring/status", headers=auth_headers())
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_monitoring_summary(self):
        resp = client.get("/monitoring/summary", headers=auth_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "total_monitored" in data
        assert "sites_up" in data
        assert "sites_down" in data

    def test_check_single_site_mocked(self):
        from services.uptime_monitor import check_single_site
        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            result = check_single_site("https://example.com")
            assert result["is_up"] == True
            assert result["http_status"] == 200


# ============================================================
# 7: ALERTS & MALWARE API
# ============================================================

class TestAlertsAPI:
    def test_list_alerts(self):
        resp = client.get("/alerts/", headers=auth_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "alerts" in data
        assert "total" in data
        assert "total_open" in data

    def test_resolve_alert(self):
        # Create an alert in DB
        db = TestSession()
        alert = models.Alert(
            type="disk_high",
            severity="warning",
            message="Test disk alert",
            is_resolved=False
        )
        db.add(alert)
        db.commit()
        alert_id = alert.id
        db.close()

        # Resolve via API
        resp = client.post(f"/alerts/{alert_id}/resolve", headers=auth_headers())
        assert resp.status_code == 200
        assert resp.json()["alert_id"] == alert_id

    def test_malware_alerts_list(self):
        resp = client.get("/alerts/malware", headers=auth_headers())
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ============================================================
# 8: NOTIFICATION SERVICE (Teams & Email Unit Tests)
# ============================================================

class TestNotificationService:
    def test_teams_alert_skipped_when_no_webhook(self):
        from services.notification_service import send_teams_alert
        alert = models.Alert(type="site_down", severity="critical", message="Test outage")
        with patch.dict(os.environ, {}, clear=True):
            res = send_teams_alert(alert, "VPS-Test")
            assert res == False

    def test_email_alert_skipped_when_no_smtp(self):
        from services.notification_service import send_email_alert
        alert = models.Alert(type="disk_high", severity="warning", message="Disk at 88%")
        with patch.dict(os.environ, {}, clear=True):
            res = send_email_alert(alert, "VPS-Test")
            assert res == False

    def test_whatsapp_alert_callmebot_mocked(self):
        from services.notification_service import send_whatsapp_alert
        alert = models.Alert(type="cpu_high", severity="critical", message="CPU at 98%")
        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.text = "Message queued"
            with patch.dict(os.environ, {"WHATSAPP_USER_PHONE": "+1234567890", "WHATSAPP_API_KEY": "dummy_key", "WHATSAPP_PROVIDER": "callmebot"}):
                res = send_whatsapp_alert(alert, "VPS-Test", target="user")
                assert res["user_sent"] == True
                assert mock_get.called

    def test_whatsapp_alert_group_mocked(self):
        from services.notification_service import send_whatsapp_alert
        alert = models.Alert(type="site_down", severity="critical", message="Outage on domain.com")
        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.text = "Message sent to group"
            with patch.dict(os.environ, {"WHATSAPP_GROUP_ID": "120363023456789@g.us", "WHATSAPP_API_KEY": "dummy_key", "WHATSAPP_PROVIDER": "callmebot"}):
                res = send_whatsapp_alert(alert, "VPS-Test", target="group")
                assert res["group_sent"] == True
                assert mock_get.called


# ============================================================
# 9: RISK ENGINE & CONFIDENCE WEIGHTING
# ============================================================

class TestRiskEngine:
    def test_healthy_server_low_risk(self):
        from services.risk_engine import calculate_server_risk
        server = MagicMock()
        server.cpu_usage = 15
        server.memory_usage = 25
        server.disk_usage = 20
        server.uptime_days = 30
        server.error_count = 0
        server.data_source = "agent"
        server.last_scanned_at = datetime.utcnow()
        server.agent_last_seen = datetime.utcnow()
        score = calculate_server_risk(server)
        assert 0 <= score <= 30

    def test_critical_server_high_risk(self):
        from services.risk_engine import calculate_server_risk
        server = MagicMock()
        server.cpu_usage = 95
        server.memory_usage = 95
        server.disk_usage = 95
        server.uptime_days = 500
        server.error_count = 60
        server.data_source = "ssh"
        server.last_scanned_at = datetime.utcnow()
        server.agent_last_seen = None
        score = calculate_server_risk(server)
        assert score >= 60

    def test_stale_data_freshness_penalty(self):
        from services.risk_engine import calculate_server_risk
        fresh_srv = MagicMock()
        fresh_srv.cpu_usage = 50
        fresh_srv.memory_usage = 50
        fresh_srv.disk_usage = 50
        fresh_srv.uptime_days = 50
        fresh_srv.error_count = 0
        fresh_srv.data_source = "agent"
        fresh_srv.last_scanned_at = datetime.utcnow()
        fresh_srv.agent_last_seen = datetime.utcnow()

        stale_srv = MagicMock()
        stale_srv.cpu_usage = 50
        stale_srv.memory_usage = 50
        stale_srv.disk_usage = 50
        stale_srv.uptime_days = 50
        stale_srv.error_count = 0
        stale_srv.data_source = "agent"
        stale_srv.last_scanned_at = datetime.utcnow() - timedelta(hours=3)
        stale_srv.agent_last_seen = datetime.utcnow() - timedelta(hours=3)

        fresh_score = calculate_server_risk(fresh_srv)
        stale_score = calculate_server_risk(stale_srv)
        assert stale_score > fresh_score, "Stale server should have a higher risk penalty"


# ============================================================
# 10: DUPLICATE DETECTION
# ============================================================

class TestDuplicateDetector:
    def _make_disc(self, id, name, server_id, git_remote=None):
        d = MagicMock()
        d.id = id
        d.project_name = name
        d.server_id = server_id
        d.domain = name
        d.git_remote = git_remote
        d.dns_points_here = True
        d.web_config_active = True
        d.size_mb = 100
        d.is_duplicate = False
        d.duplicate_confidence = 0
        d.duplicate_of_id = None
        d.duplicate_signals = None
        d.env_type = "live"
        d.recommendation = "keep"
        d.user_override = None
        return d

    def test_exact_name_cross_server_detected(self):
        from services.duplicate_detector import detect_duplicates
        a = self._make_disc(1, "app.domain.com", server_id=1)
        b = self._make_disc(2, "app.domain.com", server_id=2)
        results = detect_duplicates([a, b])
        dup_count = sum(1 for r in results if r["is_duplicate"])
        assert dup_count == 1

    def test_same_server_not_duplicate(self):
        from services.duplicate_detector import detect_duplicates
        a = self._make_disc(1, "app.domain.com", server_id=1)
        b = self._make_disc(2, "app.domain.com", server_id=1)
        results = detect_duplicates([a, b])
        dup_count = sum(1 for r in results if r["is_duplicate"])
        assert dup_count == 0


# ============================================================
# 11: CREDENTIAL ENCRYPTION
# ============================================================

class TestCredentialEncryption:
    def test_encrypt_decrypt_roundtrip(self):
        from services.credential_encryption import encrypt_credential, decrypt_credential
        original = "secret-cpanel-key-999"
        encrypted = encrypt_credential(original)
        assert encrypted != original
        decrypted = decrypt_credential(encrypted)
        assert decrypted == original


# ============================================================
# 12: ML ENGINE & STATS
# ============================================================

class TestMLEngineAndStats:
    def test_ml_status(self):
        resp = client.get("/ml/status", headers=auth_headers())
        assert resp.status_code == 200
        assert "experiment_name" in resp.json()

    def test_stats_dashboard(self):
        resp = client.get("/stats/dashboard", headers=auth_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "total_servers" in data
        assert "live_projects" in data
        assert "healthy_servers" in data
        assert "open_alerts" in data
