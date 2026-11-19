import os, tempfile
_d = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_d, "test.db")
os.environ["UPLOAD_DIR"] = os.path.join(_d, "uploads")
os.environ["ADMIN_EMAIL"] = "admin@test.bj"
os.environ["ADMIN_PASSWORD"] = "AdminPass123"
os.environ["PAYMENT_MODE"] = "demo"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["SEED_DEMO"] = "false"

import pytest
from fastapi.testclient import TestClient
from app.main import app

H = {"X-Requested-With": "agriconnect"}


@pytest.fixture(scope="session", autouse=True)
def boot():
    with TestClient(app):  # déclenche le démarrage (tables, référentiels, administrateur)
        yield


def new_client() -> TestClient:
    c = TestClient(app)
    c.headers.update(H)
    return c


def login(email: str, password: str) -> TestClient:
    c = new_client()
    r = c.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return c


@pytest.fixture(scope="session")
def admin():
    return login("admin@test.bj", "AdminPass123")
