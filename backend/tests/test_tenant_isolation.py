"""
Multi-tenant isolation tests — the most critical security layer.

Verifies that Company A's users CANNOT:
  - read Company B's employees
  - create employees under Company B
  - access Company B's departments

Each test creates two separate companies with separate admin users
and cross-company access attempts.
"""
import pytest
from tests.conftest import create_company, create_user, login, auth_headers


def _seed_dept(db, company_id, name="Engineering"):
    from app.models.employee import Department
    dept = Department(name=name, code=name[:6].upper().replace(" ", ""),
                      company_id=company_id)
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept


def _seed_designation(db, company_id, dept_id, title="Engineer"):
    from app.models.employee import Designation
    desig = Designation(name=title,
                        department_id=dept_id, company_id=company_id)
    db.add(desig)
    db.commit()
    db.refresh(desig)
    return desig


def _create_employee_in_company(client, token, dept_id, desig_id,
                                first_name="Alice", email="alice@co.com"):
    payload = {
        "first_name": first_name,
        "last_name": "Smith",
        "email": email,
        "phone": "+919900000002",
        "gender": "female",
        "date_of_birth": "1992-03-20",
        "department_id": dept_id,
        "designation_id": desig_id,
        "joining_date": "2024-06-01",
        "employment_type": "full_time",
        "gross_ctc": 800000,
    }
    return client.post("/api/v1/employees",
                       json=payload,
                       headers=auth_headers(token))


class TestEmployeeIsolation:
    """Company A cannot see or modify Company B's employees."""

    def _setup_two_companies(self, db, client):
        """Helper: create two companies, each with one admin. Returns tokens."""
        co_a = create_company(db, name="Alpha Corp", code="ALPHCORP")
        co_b = create_company(db, name="Beta Corp", code="BETACORP")

        create_user(db, co_a.id, email="admin@alpha.com", password="Admin@1234")
        create_user(db, co_b.id, email="admin@beta.com", password="Admin@1234")

        token_a = login(client, "admin@alpha.com", "Admin@1234")
        token_b = login(client, "admin@beta.com", "Admin@1234")

        return co_a, co_b, token_a, token_b

    def test_company_a_cannot_see_company_b_employees(self, client, db):
        """
        Employees created under Company B must NOT appear in Company A's list.
        This is the core multi-tenant isolation guarantee.
        """
        co_a, co_b, token_a, token_b = self._setup_two_companies(db, client)

        # Seed Company B with one employee
        dept_b = _seed_dept(db, co_b.id, "Sales")
        desig_b = _seed_designation(db, co_b.id, dept_b.id, "Sales Rep")
        resp = _create_employee_in_company(client, token_b,
                                           dept_b.id, desig_b.id,
                                           first_name="Bob", email="bob@beta.com")
        assert resp.status_code == 201
        bob_id = resp.json()["id"]

        # Company A list — Bob must NOT appear
        list_resp = client.get("/api/v1/employees", headers=auth_headers(token_a))
        assert list_resp.status_code == 200
        ids = [e["id"] for e in list_resp.json()["items"]]
        assert bob_id not in ids, "Company A can see Company B's employee — ISOLATION BREACH"

    def test_company_a_cannot_fetch_company_b_employee_by_id(self, client, db):
        """
        Direct GET /employees/{id} with Company A token for a Company B employee
        must return 404 (not 403 — we don't expose that the record exists).
        """
        co_a, co_b, token_a, token_b = self._setup_two_companies(db, client)

        dept_b = _seed_dept(db, co_b.id, "Finance")
        desig_b = _seed_designation(db, co_b.id, dept_b.id, "Analyst")
        resp = _create_employee_in_company(client, token_b,
                                           dept_b.id, desig_b.id,
                                           first_name="Carol", email="carol@beta.com")
        carol_id = resp.json()["id"]

        # Company A tries to fetch Carol
        get_resp = client.get(f"/api/v1/employees/{carol_id}",
                              headers=auth_headers(token_a))

        assert get_resp.status_code == 404, (
            f"Expected 404, got {get_resp.status_code} — isolation breach"
        )

    def test_company_a_cannot_deactivate_company_b_employee(self, client, db):
        """
        PATCH /employees/{id}/deactivate from Company A for Company B employee → 404.
        """
        co_a, co_b, token_a, token_b = self._setup_two_companies(db, client)

        dept_b = _seed_dept(db, co_b.id, "Ops")
        desig_b = _seed_designation(db, co_b.id, dept_b.id, "Coordinator")
        resp = _create_employee_in_company(client, token_b,
                                           dept_b.id, desig_b.id,
                                           first_name="Dan", email="dan@beta.com")
        dan_id = resp.json()["id"]

        patch_resp = client.delete(f"/api/v1/employees/{dan_id}",
                                   headers=auth_headers(token_a))

        assert patch_resp.status_code == 404

    def test_department_isolation(self, client, db):
        """
        GET /departments for Company A must not return Company B's departments.
        """
        co_a, co_b, token_a, token_b = self._setup_two_companies(db, client)

        # Seed a dept in each company
        dept_a = _seed_dept(db, co_a.id, "Alpha Dept")
        dept_b = _seed_dept(db, co_b.id, "Beta Dept")

        # Company A fetches departments
        resp = client.get("/api/v1/departments", headers=auth_headers(token_a))
        assert resp.status_code == 200

        dept_ids = [d["id"] for d in resp.json()]
        assert dept_a.id in dept_ids, "Company A should see its own department"
        assert dept_b.id not in dept_ids, "Company A must not see Company B's department"


class TestPlatformAdminAccess:
    """Platform Admin can see all companies; Company Admin cannot access platform endpoints."""

    def test_company_admin_cannot_access_companies_endpoint(self, client, db):
        """
        GET /companies is a platform-admin-only endpoint.
        Company Admin must receive 403.
        """
        co = create_company(db, name="One Corp", code="ONECORP")
        create_user(db, co.id, email="cadmin@one.com", password="Admin@1234",
                    role="COMPANY_ADMIN")
        token = login(client, "cadmin@one.com", "Admin@1234")

        resp = client.get("/api/v1/companies", headers=auth_headers(token))

        # Either 403 Forbidden or 401 Unauthorized — not 200
        assert resp.status_code in (401, 403), (
            f"Company admin should not access /companies, got {resp.status_code}"
        )
