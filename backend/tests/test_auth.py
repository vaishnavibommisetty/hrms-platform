"""
Auth tests — login, token validation, /me endpoint, password change.

Covers:
  - Positive: valid credentials return 200 + JWT
  - Negative: wrong password, unknown email → 401
  - Token: /me returns correct user info
  - Boundary: empty email, empty password
"""
import pytest
from tests.conftest import create_company, create_user, login, auth_headers


class TestLogin:
    """POST /api/v1/auth/login"""

    def test_login_valid_credentials(self, client, db):
        """Happy path: correct email + password returns 200 with JWT."""
        co = create_company(db)
        create_user(db, co.id, email="hr@corp.com", password="Secure@123")

        resp = client.post("/api/v1/auth/login",
                           json={"email": "hr@corp.com", "password": "Secure@123"})

        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 20  # real JWT, not empty

    def test_login_wrong_password(self, client, db):
        """Wrong password → 401 Unauthorized."""
        co = create_company(db)
        create_user(db, co.id, email="hr@corp.com", password="Correct@123")

        resp = client.post("/api/v1/auth/login",
                           json={"email": "hr@corp.com", "password": "Wrong@999"})

        assert resp.status_code == 401

    def test_login_unknown_email(self, client, db):
        """Email not in DB → 401 (not 404, to avoid user enumeration)."""
        resp = client.post("/api/v1/auth/login",
                           json={"email": "ghost@nowhere.com", "password": "Any@123"})

        assert resp.status_code == 401

    def test_login_inactive_user(self, client, db):
        """Deactivated user cannot log in."""
        from app.models.user import User
        co = create_company(db)
        user = create_user(db, co.id, email="inactive@corp.com", password="Admin@1234")
        # Deactivate
        db.query(User).filter(User.id == user.id).update({"is_active": False})
        db.commit()

        resp = client.post("/api/v1/auth/login",
                           json={"email": "inactive@corp.com", "password": "Admin@1234"})

        assert resp.status_code == 401

    def test_login_empty_email(self, client, db):
        """Empty email → 422 Unprocessable Entity."""
        resp = client.post("/api/v1/auth/login",
                           json={"email": "", "password": "Admin@1234"})
        assert resp.status_code == 422

    def test_login_empty_password(self, client, db):
        """Empty password string → credentials invalid → 401 Unauthorized.

        Note: Pydantic allows empty string (no min_length constraint on password
        in login schema), so validation passes; auth logic returns 401.
        """
        resp = client.post("/api/v1/auth/login",
                           json={"email": "admin@corp.com", "password": ""})
        assert resp.status_code == 401

    def test_login_missing_body(self, client, db):
        """No JSON body → 422."""
        resp = client.post("/api/v1/auth/login")
        assert resp.status_code == 422


class TestMe:
    """GET /api/v1/auth/me"""

    def test_me_returns_current_user(self, client, db):
        """Valid token → returns correct user info."""
        co = create_company(db)
        create_user(db, co.id, email="me@corp.com", password="Admin@1234",
                    role="HR_MANAGER")
        token = login(client, "me@corp.com", "Admin@1234")

        resp = client.get("/api/v1/auth/me", headers=auth_headers(token))

        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "me@corp.com"
        assert data["role"].upper() == "HR_MANAGER"  # API returns lowercase enum value

    def test_me_no_token(self, client, db):
        """No Authorization header → 401."""
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    def test_me_invalid_token(self, client, db):
        """Garbage token → 401."""
        resp = client.get("/api/v1/auth/me",
                          headers={"Authorization": "Bearer not_a_real_token"})
        assert resp.status_code == 401

    def test_me_expired_token(self, client, db):
        """Manually crafted expired token → 401."""
        import time
        from jose import jwt
        from app.core.config import settings

        # Create a token that expired 1 second ago
        payload = {
            "sub": "999",
            "exp": int(time.time()) - 1,  # already expired
            "role": "EMPLOYEE",
            "company_id": 1,
        }
        expired_token = jwt.encode(payload, settings.SECRET_KEY,
                                   algorithm=settings.ALGORITHM)

        resp = client.get("/api/v1/auth/me",
                          headers={"Authorization": f"Bearer {expired_token}"})
        assert resp.status_code == 401
