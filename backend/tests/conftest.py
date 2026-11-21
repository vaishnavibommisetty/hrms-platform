"""
Pytest configuration and shared fixtures for HRMS Platform tests.

Uses an in-memory SQLite database — completely isolated from hrms.db.
Each test function gets a fresh DB via the `db` fixture.

Architecture note: The FastAPI TestClient and the `db` fixture must share
the SAME SQLite in-memory database connection. We achieve this by:
1. Using a single engine with a fixed in-memory URL with a shared cache (uri=True)
2. Overriding get_db dependency to use the same session factory
3. Creating tables before each test, dropping after
"""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

# Set env BEFORE importing any app module
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key-for-pytest-only"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "480"

from app.main import app as fastapi_app
from app.core.database import Base, get_db
import app.models  # noqa: F401 — register all ORM models with Base.metadata


# ── Shared in-memory engine ──────────────────────────────────────────────────
# "check_same_thread=False" needed because FastAPI + TestClient may use threads.
# We use a single connection and pass it to all sessions so the in-memory DB
# is shared (in-memory DBs are per-connection by default in SQLite).

@pytest.fixture(scope="function")
def db():
    """
    Session fixture that also configures the app's dependency override.

    Key insight for SQLite in-memory: a new connection = new empty database.
    We keep ONE connection open for the test's entire lifetime and bind all
    sessions to it. The app's DB override uses the same connection so it sees
    all data the test seeds.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool

    # StaticPool keeps one connection alive — all sessions share it
    _engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    Base.metadata.create_all(bind=_engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)

    def override_get_db():
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    # Wire the override into the FastAPI app instance
    fastapi_app.dependency_overrides[get_db] = override_get_db

    session = SessionLocal()
    yield session
    session.close()

    # Cleanup
    fastapi_app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=_engine)
    _engine.dispose()


@pytest.fixture(scope="function")
def client(db):  # db fixture must run first to set up dependency override
    """FastAPI TestClient — dependency override is already set up by `db`."""
    with TestClient(fastapi_app, raise_server_exceptions=True) as c:
        yield c


# ── Seed helpers ─────────────────────────────────────────────────────────────

def create_company(db, name="Test Corp", code="TSTCORP"):
    from app.models.company import Company
    co = Company(name=name, code=code, industry="Technology")
    db.add(co)
    db.commit()
    db.refresh(co)
    return co


def create_user(db, company_id, email="admin@test.com",
                password="Admin@1234", role="COMPANY_ADMIN"):
    from app.models.user import User, UserRole
    from app.core.security import hash_password
    user = User(
        email=email,
        hashed_password=hash_password(password),
        full_name="Test Admin",
        role=UserRole[role],
        company_id=company_id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def login(client, email="admin@test.com", password="Admin@1234") -> str:
    """Helper: login and return Bearer token string."""
    resp = client.post("/api/v1/auth/login",
                       json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed ({resp.status_code}): {resp.text}"
    return resp.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
