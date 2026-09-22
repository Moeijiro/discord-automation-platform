"""Authentication: every guild route is closed until a session exists."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.conftest import MANAGED_GUILD

PROTECTED = [
    ("get", "/api/me", None),
    ("get", "/api/guilds", None),
    ("get", f"/api/guilds/{MANAGED_GUILD}", None),
    ("get", f"/api/guilds/{MANAGED_GUILD}/settings", None),
    ("get", f"/api/guilds/{MANAGED_GUILD}/logs", None),
    ("patch", f"/api/guilds/{MANAGED_GUILD}/settings", {"welcome_enabled": False}),
    ("post", f"/api/guilds/{MANAGED_GUILD}/verify", {}),
    (
        "post",
        f"/api/guilds/{MANAGED_GUILD}/roles/add",
        {"user_id": "900000000000000009", "role_id": "200000000000000011"},
    ),
]


@pytest.mark.parametrize("method,path,body", PROTECTED)
def test_routes_require_authentication(
    client: TestClient, method: str, path: str, body: dict | None
) -> None:
    response = getattr(client, method)(path, json=body) if body is not None else getattr(client, method)(path)
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated."


def test_health_is_public(client: TestClient) -> None:
    payload = client.get("/api/health").json()
    assert payload["status"] == "ok"
    assert payload["mode"] == "demo"


def test_login_issues_httponly_session_cookie(client: TestClient) -> None:
    response = client.get("/api/auth/login", follow_redirects=False)
    assert response.status_code == 302

    callback = response.headers["location"].replace("http://localhost:8000", "")
    final = client.get(callback, follow_redirects=False)
    assert final.status_code == 302
    assert final.headers["location"].endswith("/dashboard")

    cookie = final.headers["set-cookie"]
    assert "dap_session=" in cookie
    assert "HttpOnly" in cookie


def test_callback_rejects_a_forged_state(client: TestClient) -> None:
    client.get("/api/auth/login", follow_redirects=False)
    response = client.get(
        "/api/auth/callback?code=demo&state=not-the-state-we-issued",
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "error=invalid_state" in response.headers["location"]
    assert "dap_session" not in response.headers.get("set-cookie", "")


def test_session_is_rejected_when_tampered_with(auth_client: TestClient) -> None:
    auth_client.cookies.set("dap_session", "not.a.valid.jwt")
    assert auth_client.get("/api/me").status_code == 401


def test_logout_clears_the_session(auth_client: TestClient) -> None:
    assert auth_client.post("/api/auth/logout").status_code == 204
    auth_client.cookies.clear()
    assert auth_client.get("/api/me").status_code == 401


def test_me_never_exposes_oauth_tokens(auth_client: TestClient) -> None:
    payload = auth_client.get("/api/me").json()
    assert set(payload) == {
        "discord_id",
        "username",
        "global_name",
        "avatar",
        "display_name",
        "avatar_url",
    }
