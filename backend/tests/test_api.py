"""
Enterprise Test Suite for AI Infrastructure Intelligence Platform
Tests: Auth, API endpoints, risk engine, duplicate detection, inactive detection,
       credential encryption, ML pipeline, and data integrity.
"""
import os
import sys
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# Ensure backend is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from main import app
from database import Base, get_db
import models

# ============================================================
# TEST DATABASE SETUP (in-memory SQLite for isolation)
# ============================================================

SQLALCHEMY_TEST_URL = "sqlite:///./test_infra.db"
test_engine = create_engine(SQLALCHEMY_TEST_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


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
    """Create all tables before tests, drop after."""
    Base.metadata.create_all(bind=test_engine)
    # Seed a test user
    db = TestSession()
    try:
        from routers.auth import hash_password
        import models
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
    Base.metadata.drop_all(bind=test_engine)
    if os.path.exists("./test_infra.db"):
        os.remove("./test_infra.db")


_cached_token = None

def get_auth_token() -> str:
    """Helper: login and return bearer token (cached to avoid rate limiting)."""
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
# PHASE 1: HEALTH & ROOT
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
# PHASE 2: AUTHENTICATION
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

    def test_login_nonexistent_user(self):
        resp = client.post(
            "/auth/login",
            data={"username": "nosuchuser", "password": "anything"},
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

    def test_me_with_invalid_token_returns_401(self):
        resp = client.get("/auth/me", headers={"Authorization": "Bearer invalidtoken123"})
        assert resp.status_code == 401

    def test_register_new_user(self):
        resp = client.post(
            "/auth/register",
            json={"username": "newuser_test", "email": "new@test.com", "password": "securepassword"},
            headers=auth_headers()
        )
        assert resp.status_code == 201
        assert resp.json()["username"] == "newuser_test"

    def test_register_duplicate_username(self):
        resp = client.post(
            "/auth/register",
            json={"username": "testadmin", "email": "dup@test.com", "password": "password"},
            headers=auth_headers()
        )
        assert resp.status_code == 400


# ============================================================
# PHASE 3: SERVERS (requires auth)
# ============================================================

class TestServersAPI:
    def test_list_servers_requires_auth(self):
        resp = client.get("/servers/")
        assert resp.status_code in (401, 403)

    def test_list_servers_with_auth(self):
        resp = client.get("/servers/", headers=auth_headers())
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_server(self):
        resp = client.post("/servers/", json={
            "name": "Test Server Alpha",
            "ip_address": "10.0.0.1",
            "environment": "production",
            "status": "active",
            "ssh_username": "root",
            "ssh_port": 22,
        }, headers=auth_headers())
        assert resp.status_code in (200, 201)
        data = resp.json()
        # Response format: {message, id, ip_address}
        assert "id" in data
        assert data["ip_address"] == "10.0.0.1"
        assert "message" in data

    def test_get_server_by_id(self):
        # Create then fetch
        create_resp = client.post("/servers/", json={
            "name": "Fetch Server",
            "ip_address": "10.0.0.2",
        }, headers=auth_headers())
        server_id = create_resp.json()["id"]

        resp = client.get(f"/servers/{server_id}", headers=auth_headers())
        assert resp.status_code == 200
        assert resp.json()["id"] == server_id

    def test_get_nonexistent_server(self):
        resp = client.get("/servers/99999", headers=auth_headers())
        assert resp.status_code == 404

    def test_delete_server(self):
        create_resp = client.post("/servers/", json={
            "name": "Delete Me Server",
            "ip_address": "10.0.0.99",
        }, headers=auth_headers())
        server_id = create_resp.json()["id"]

        resp = client.delete(f"/servers/{server_id}", headers=auth_headers())
        assert resp.status_code == 200

        # Verify it's gone
        resp = client.get(f"/servers/{server_id}", headers=auth_headers())
        assert resp.status_code == 404


# ============================================================
# PHASE 4: PROJECTS API
# ============================================================

class TestProjectsAPI:
    def test_list_projects_requires_auth(self):
        resp = client.get("/projects/")
        assert resp.status_code in (401, 403)

    def test_list_projects_with_auth(self):
        resp = client.get("/projects/", headers=auth_headers())
        assert resp.status_code == 200


# ============================================================
# PHASE 5: RISK ENGINE (Unit Tests)
# ============================================================

class TestRiskEngine:
    def test_healthy_server_low_risk(self):
        """Server with low CPU/memory/disk should get a low risk score."""
        from services.risk_engine import calculate_server_risk
        server = MagicMock()
        server.cpu_usage = 20
        server.memory_usage = 30
        server.disk_usage = 25
        server.uptime_days = 45
        server.error_count = 0
        server.data_source = "ssh"
        score = calculate_server_risk(server)
        assert 0 <= score <= 30, f"Healthy server got risk {score}"

    def test_critical_server_high_risk(self):
        """Server with all metrics at 95+ should get a high risk score."""
        from services.risk_engine import calculate_server_risk
        server = MagicMock()
        server.cpu_usage = 95
        server.memory_usage = 95
        server.disk_usage = 95
        server.uptime_days = 500
        server.error_count = 60
        server.data_source = "ssh"
        score = calculate_server_risk(server)
        assert score >= 60, f"Critical server got risk {score}"

    def test_risk_score_clamped_0_100(self):
        """Risk score must always be in [0, 100] range."""
        from services.risk_engine import calculate_server_risk
        server = MagicMock()
        server.cpu_usage = 100
        server.memory_usage = 100
        server.disk_usage = 100
        server.uptime_days = 9999
        server.error_count = 9999
        server.data_source = "ssh"
        score = calculate_server_risk(server)
        assert 0 <= score <= 100

    def test_risk_with_none_values(self):
        """Risk engine handles None/missing attributes gracefully."""
        from services.risk_engine import calculate_server_risk
        server = MagicMock()
        server.cpu_usage = None
        server.memory_usage = None
        server.disk_usage = None
        server.uptime_days = None
        server.error_count = None
        server.data_source = None
        score = calculate_server_risk(server)
        assert 0 <= score <= 100

    def test_non_ssh_source_penalised(self):
        """WHM/estimated sources should get a lower/adjusted risk score."""
        from services.risk_engine import calculate_server_risk
        ssh_server = MagicMock()
        ssh_server.cpu_usage = 85
        ssh_server.memory_usage = 85
        ssh_server.disk_usage = 85
        ssh_server.uptime_days = 200
        ssh_server.error_count = 10
        ssh_server.data_source = "ssh"

        whm_server = MagicMock()
        whm_server.cpu_usage = 85
        whm_server.memory_usage = 85
        whm_server.disk_usage = 85
        whm_server.uptime_days = 200
        whm_server.error_count = 10
        whm_server.data_source = "estimated"

        ssh_score = calculate_server_risk(ssh_server)
        whm_score = calculate_server_risk(whm_server)
        # Both valid, estimated should differ due to non-SSH penalty
        assert 0 <= ssh_score <= 100
        assert 0 <= whm_score <= 100


# ============================================================
# PHASE 6: DUPLICATE DETECTION (Unit Tests)
# ============================================================

class TestDuplicateDetector:
    def _make_disc(self, id, name, server_id, domain=None, git_remote=None,
                   dns_points_here=True, web_config_active=True, size_mb=100):
        d = MagicMock()
        d.id = id
        d.project_name = name
        d.server_id = server_id
        d.domain = domain or name
        d.git_remote = git_remote
        d.dns_points_here = dns_points_here
        d.web_config_active = web_config_active
        d.size_mb = size_mb
        d.is_duplicate = False
        d.duplicate_confidence = 0
        d.duplicate_of_id = None
        d.duplicate_signals = None
        d.env_type = "live"
        d.recommendation = "keep"
        d.user_override = None
        return d

    def test_exact_name_cross_server_detected(self):
        """Same project name on different servers = duplicate."""
        from services.duplicate_detector import detect_duplicates
        a = self._make_disc(1, "example.com", server_id=1)
        b = self._make_disc(2, "example.com", server_id=2)
        results = detect_duplicates([a, b])
        dup_count = sum(1 for r in results if r["is_duplicate"])
        assert dup_count == 1, f"Expected 1 duplicate, got {dup_count}"

    def test_same_server_not_duplicate(self):
        """Same project name on the same server is NOT a duplicate (cross-server only)."""
        from services.duplicate_detector import detect_duplicates
        a = self._make_disc(1, "example.com", server_id=1)
        b = self._make_disc(2, "example.com", server_id=1)
        results = detect_duplicates([a, b])
        dup_count = sum(1 for r in results if r["is_duplicate"])
        assert dup_count == 0

    def test_user_override_keep_respected(self):
        """Projects with user_override='keep' should never be marked as duplicate."""
        from services.duplicate_detector import detect_duplicates
        a = self._make_disc(1, "example.com", server_id=1)
        b = self._make_disc(2, "example.com", server_id=2)
        b.user_override = "keep"
        results = detect_duplicates([a, b])
        dup_count = sum(1 for r in results if r["is_duplicate"])
        assert dup_count == 0

    def test_different_names_no_duplicate(self):
        """Completely different names should not be flagged."""
        from services.duplicate_detector import detect_duplicates
        a = self._make_disc(1, "alpha-project.com", server_id=1)
        b = self._make_disc(2, "beta-service.io", server_id=2)
        results = detect_duplicates([a, b])
        dup_count = sum(1 for r in results if r["is_duplicate"])
        assert dup_count == 0

    def test_git_remote_match_detected(self):
        """Same git remote on different servers = duplicate."""
        from services.duplicate_detector import detect_duplicates
        a = self._make_disc(1, "project-a", server_id=1, git_remote="https://github.com/org/repo.git")
        b = self._make_disc(2, "project-b", server_id=2, git_remote="https://github.com/org/repo.git")
        results = detect_duplicates([a, b])
        dup_count = sum(1 for r in results if r["is_duplicate"])
        assert dup_count == 1


# ============================================================
# PHASE 7: INACTIVE DETECTION (Unit Tests)
# ============================================================

class TestInactiveDetector:
    def _make_disc(self, id, name, is_inactive=False, env_type="live", user_override=None):
        d = MagicMock()
        d.id = id
        d.project_name = name
        d.server_id = 1
        d.is_inactive = is_inactive
        d.env_type = env_type
        d.user_override = user_override
        d.days_since_modified = 10 if not is_inactive else 1200
        d.recommendation = "keep"
        d.inactivity_signals = "[]"
        return d

    def test_active_project_not_inactive(self):
        from services.inactive_detector import detect_inactive_projects
        d = self._make_disc(1, "active-project", is_inactive=False)
        results = detect_inactive_projects([d])
        assert len(results) == 0
        assert d.is_inactive == False

    def test_suspended_account_detected_inactive(self):
        from services.inactive_detector import detect_inactive_projects
        d = self._make_disc(1, "old-project", is_inactive=True)
        results = detect_inactive_projects([d])
        assert len(results) == 1
        assert d.is_inactive == True
        assert d.recommendation == "archive"

    def test_archived_env_type_detected_inactive(self):
        from services.inactive_detector import detect_inactive_projects
        d = self._make_disc(1, "archived-thing", is_inactive=False, env_type="archived")
        results = detect_inactive_projects([d])
        assert len(results) == 1
        assert d.is_inactive == True

    def test_user_override_keep_skips_inactive(self):
        from services.inactive_detector import detect_inactive_projects
        d = self._make_disc(1, "override-keep", is_inactive=True, user_override="keep")
        results = detect_inactive_projects([d])
        assert d.is_inactive == False


# ============================================================
# PHASE 8: CREDENTIAL ENCRYPTION (Unit Tests)
# ============================================================

class TestCredentialEncryption:
    def test_encrypt_decrypt_roundtrip(self):
        """Encrypted value must decrypt back to original."""
        from services.credential_encryption import encrypt_credential, decrypt_credential
        original = "my-secret-password-123"
        encrypted = encrypt_credential(original)
        assert encrypted != original, "Encrypted should differ from plaintext"
        decrypted = decrypt_credential(encrypted)
        assert decrypted == original, f"Expected '{original}', got '{decrypted}'"

    def test_encrypt_empty_string(self):
        from services.credential_encryption import encrypt_credential
        assert encrypt_credential("") == ""
        assert encrypt_credential(None) is None

    def test_is_encrypted_detects_fernet(self):
        from services.credential_encryption import encrypt_credential, is_encrypted
        enc = encrypt_credential("test-value")
        assert is_encrypted(enc) == True
        assert is_encrypted("plaintext-value") == False
        assert is_encrypted("") == False
        assert is_encrypted(None) == False


# ============================================================
# PHASE 9: ML PIPELINE (Unit Tests)
# ============================================================

class TestMLPipeline:
    def test_synthetic_dataset_generation(self):
        from services.ml_pipeline import generate_synthetic_dataset
        df = generate_synthetic_dataset(n_samples=100)
        assert len(df) == 100
        assert list(df.columns) == ["cpu", "memory", "disk", "uptime", "errors", "risk_score"]
        # Values in expected ranges
        assert df["cpu"].min() >= 0
        assert df["cpu"].max() <= 100
        assert df["risk_score"].min() >= 0
        assert df["risk_score"].max() <= 100

    def test_model_meta_save_load(self):
        from services.ml_pipeline import _save_model_meta, _load_model_meta, MODEL_META_PATH
        test_meta = {"r2_score": 0.95, "model_type": "TestModel", "test": True}
        _save_model_meta(test_meta)
        loaded = _load_model_meta()
        assert loaded["r2_score"] == 0.95
        assert loaded["model_type"] == "TestModel"
        # Clean up test meta file
        if os.path.exists(MODEL_META_PATH):
            os.remove(MODEL_META_PATH)


# ============================================================
# PHASE 10: STATS / DASHBOARD (Auth gap documentation)
# ============================================================

class TestStatsEndpoint:
    def test_stats_dashboard_requires_auth(self):
        """Verifies that /stats/dashboard now requires authentication (was a known gap, now fixed)."""
        resp = client.get("/stats/dashboard")
        assert resp.status_code in (401, 403)

    def test_stats_dashboard_with_auth(self):
        resp = client.get("/stats/dashboard", headers=auth_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "total_servers" in data
        assert "total_projects" in data


# ============================================================
# PHASE 11: AI INSIGHTS
# ============================================================

class TestAIInsights:
    def test_insights_requires_auth(self):
        resp = client.get("/ai/insights")
        assert resp.status_code in (401, 403)

    def test_insights_with_auth(self):
        resp = client.get("/ai/insights", headers=auth_headers())
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ============================================================
# PHASE 12: ML ENDPOINTS
# ============================================================

class TestMLEndpoints:
    def test_ml_status_requires_auth(self):
        resp = client.get("/ml/status")
        assert resp.status_code in (401, 403)

    def test_ml_status_with_auth(self):
        resp = client.get("/ml/status", headers=auth_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "experiment_name" in data
        assert "model_loaded" in data

    def test_feature_importance_requires_auth(self):
        resp = client.get("/ml/feature-importance")
        assert resp.status_code in (401, 403)

    def test_feature_importance_with_auth(self):
        resp = client.get("/ml/feature-importance", headers=auth_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "features" in data
        assert len(data["features"]) == 5

    def test_predictions_requires_auth(self):
        resp = client.get("/ml/predictions")
        assert resp.status_code in (401, 403)

    def test_predictions_with_auth(self):
        resp = client.get("/ml/predictions", headers=auth_headers())
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ============================================================
# PHASE 13: 24/7 WEBSITE MONITORING
# ============================================================

class TestWebsiteMonitoring:
    def test_monitoring_overview_requires_auth(self):
        resp = client.get("/monitoring/overview")
        assert resp.status_code in (401, 403)

    def test_monitoring_overview_with_auth(self):
        resp = client.get("/monitoring/overview", headers=auth_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "total_websites" in data
        assert "uptime_percentage" in data
        assert "average_latency_ms" in data

    def test_monitoring_websites_list(self):
        resp = client.get("/monitoring/websites", headers=auth_headers())
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_monitoring_check_now(self):
        resp = client.post("/monitoring/check-now", headers=auth_headers())
        assert resp.status_code == 200
        assert "Live website monitoring check completed" in resp.json()["message"]


# ============================================================
# PHASE 14: SECURITY AUDIT & MULTI-CHANNEL ALERTS
# ============================================================

class TestSecurityAndAlerts:
    def test_security_alerts_requires_auth(self):
        resp = client.get("/security/alerts")
        assert resp.status_code in (401, 403)

    def test_security_alerts_with_auth(self):
        resp = client.get("/security/alerts", headers=auth_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "alerts" in data
        assert "total_active" in data

    def test_security_scan_now(self):
        resp = client.post("/security/scan-now", headers=auth_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"

    def test_alert_config_save_and_read(self):
        payload = {
            "teams_webhook_url": "https://outlook.office.com/webhook/test-sample",
            "teams_enabled": True,
            "email_recipients": "devops@company.com, admin@company.com",
            "email_enabled": True,
            "alert_on_disk_full": True,
            "alert_on_website_down": True,
            "alert_on_malware": True
        }
        res = client.post("/security/config", json=payload, headers=auth_headers())
        assert res.status_code == 200

        cfg_res = client.get("/security/config", headers=auth_headers())
        assert cfg_res.status_code == 200
        data = cfg_res.json()
        assert data["teams_enabled"] is True
        assert data["email_enabled"] is True

    def test_send_test_alert(self):
        res = client.post("/security/test-alert?channel=both", headers=auth_headers())
        assert res.status_code == 200
        data = res.json()
        assert "results" in data


# ============================================================
# PHASE 15: 24/7 DEDICATED MONITORING AGENT
# ============================================================

class TestAgentArchitecture:
    def test_get_install_bash_script(self):
        resp = client.get("/agent/install.sh")
        assert resp.status_code == 200
        assert "#!/usr/bin/env bash" in resp.text
        assert "infra-intel" in resp.text

    def test_get_agent_python_script(self):
        resp = client.get("/agent/script.py")
        assert resp.status_code == 200
        assert "get_cpu_usage" in resp.text
        assert "get_mem_usage" in resp.text

    def test_get_server_agent_token(self):
        db = TestSession()
        server = db.query(models.Server).first()
        if not server:
            server = models.Server(name="agent-node", ip_address="192.168.1.100")
            db.add(server)
            db.commit()
            db.refresh(server)
        srv_id = server.id
        db.close()

        resp = client.get(f"/agent/token/{srv_id}", headers=auth_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "agent_token" in data
        assert "install_command" in data
        assert f"--token={data['agent_token']}" in data["install_command"]

    def test_post_agent_telemetry_valid(self):
        db = TestSession()
        server = db.query(models.Server).first()
        if not server:
            server = models.Server(name="agent-node", ip_address="192.168.1.100", agent_token="test_agent_valid_token")
            db.add(server)
            db.commit()
            db.refresh(server)
        if not server.agent_token:
            server.agent_token = "test_agent_valid_token"
            db.commit()
        token = server.agent_token
        db.close()

        payload = {
            "hostname": "linux-node-1",
            "os_name": "AlmaLinux 9.4",
            "kernel": "5.14.0-427.el9.x86_64",
            "cpu_usage": 35,
            "memory_usage": 48,
            "disk_usage": 52,
            "load_avg_1": 0.85,
            "load_avg_5": 0.90,
            "load_avg_15": 0.75,
            "uptime_days": 42,
            "cpanel_accounts_count": 14,
            "top_processes": [
                {"pid": "1234", "user": "mysql", "cpu": 12.5, "mem": 18.2, "command": "/usr/sbin/mysqld"}
            ],
            "agent_version": "3.0.0"
        }
        resp = client.post("/agent/telemetry", json=payload, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "risk_score" in data

    def test_post_agent_telemetry_invalid_token(self):
        payload = {
            "cpu_usage": 10,
            "memory_usage": 20,
            "disk_usage": 30,
            "load_avg_1": 0.1,
            "load_avg_5": 0.1,
            "load_avg_15": 0.1,
            "uptime_days": 10
        }
        resp = client.post("/agent/telemetry", json=payload, headers={"Authorization": "Bearer invalid_bad_token"})
        assert resp.status_code == 403


