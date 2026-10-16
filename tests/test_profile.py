"""Profile, background CRUD, ownership, and GDPR-style deletion."""

from __future__ import annotations

from sqlalchemy import func, select

from app.models import Certificate, Profile, User
from tests.conftest import register


async def test_profile_created_on_register(auth_client):
    resp = await auth_client.get("/api/v1/me/profile")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] is None and body["completeness"] == 0


async def test_patch_profile(auth_client):
    resp = await auth_client.patch(
        "/api/v1/me/profile",
        json={
            "status": "student",
            "target_role": "Python developer",
            "weekly_hours": 6,
            "linkedin_url": "https://www.linkedin.com/in/sara",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "student" and body["weekly_hours"] == 6
    assert body["completeness"] > 0


async def test_profile_validation(auth_client):
    bad_hours = await auth_client.patch("/api/v1/me/profile", json={"weekly_hours": 500})
    assert bad_hours.status_code == 422
    bad_url = await auth_client.patch(
        "/api/v1/me/profile", json={"linkedin_url": "https://evil.com/x"}
    )
    assert bad_url.status_code == 422


async def test_html_profile_form_blank_fields(auth_client):
    """Blank optional fields from an HTML form must not break NOT NULL columns."""
    form = {
        "status": "job_seeker",
        "target_role": "Data analyst",
        "weekly_hours": "",
        "preferred_language": "",
        "budget": "free",
        "goal_date": "",
    }
    resp = await auth_client.post("/profile/edit", data=form)
    assert resp.status_code == 303
    body = (await auth_client.get("/api/v1/me/profile")).json()
    assert body["preferred_language"] == "English" and body["budget"] == "free"


async def test_certificate_crud_and_ownership(client):
    await register(client, "a@example.com")
    created = await client.post(
        "/api/v1/me/certificates",
        json={"name": "Python for Everybody", "issuer": "Coursera", "issue_date": "2025-05-01"},
    )
    assert created.status_code == 201
    cert_id = created.json()["id"]

    # A second user cannot delete the first user's certificate.
    client.cookies.clear()
    await register(client, "b@example.com")
    assert (await client.delete(f"/api/v1/me/certificates/{cert_id}")).status_code == 404
    assert (await client.get("/api/v1/me/certificates")).json() == []


async def test_experience_and_project(auth_client):
    exp = await auth_client.post(
        "/api/v1/me/experiences",
        json={"title": "Intern", "kind": "internship", "organization": "ACME"},
    )
    assert exp.status_code == 201
    proj = await auth_client.post(
        "/api/v1/me/projects",
        json={"name": "Todo API", "technologies": ["Python", "FastAPI"]},
    )
    assert proj.status_code == 201 and proj.json()["technologies"] == ["Python", "FastAPI"]
    page = await auth_client.get("/profile")
    assert page.status_code == 200 and "Todo API" in page.text and "Intern" in page.text


async def test_delete_account_removes_everything(auth_client, db):
    await auth_client.post("/api/v1/me/certificates", json={"name": "Cert"})
    resp = await auth_client.delete("/api/v1/me")
    assert resp.status_code == 200
    for model in (User, Profile, Certificate):
        count = (await db.execute(select(func.count()).select_from(model))).scalar_one()
        assert count == 0, model.__name__
    assert (await auth_client.get("/api/v1/auth/me")).status_code == 401
