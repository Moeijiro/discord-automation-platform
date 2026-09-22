"""Permission gate: membership, Manage Server, and who may verify whom."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import MANAGED_GUILD, READ_ONLY_GUILD, UNKNOWN_GUILD


def test_guild_list_marks_which_servers_are_manageable(auth_client: TestClient) -> None:
    guilds = {item["id"]: item for item in auth_client.get("/api/guilds").json()}
    assert guilds[MANAGED_GUILD]["manageable"] is True
    assert guilds[READ_ONLY_GUILD]["manageable"] is False


def test_unknown_guild_is_not_confirmed_to_exist(auth_client: TestClient) -> None:
    """A guild the caller has no membership in answers 404, never 403."""
    response = auth_client.get(f"/api/guilds/{UNKNOWN_GUILD}")
    assert response.status_code == 404


def test_settings_require_manage_server(auth_client: TestClient) -> None:
    response = auth_client.patch(
        f"/api/guilds/{READ_ONLY_GUILD}/settings", json={"welcome_enabled": False}
    )
    assert response.status_code == 403
    assert "Manage Server" in response.json()["detail"]


def test_reading_settings_only_needs_membership(auth_client: TestClient) -> None:
    assert auth_client.get(f"/api/guilds/{READ_ONLY_GUILD}/settings").status_code == 200


def test_role_actions_require_manage_server(auth_client: TestClient) -> None:
    response = auth_client.post(
        f"/api/guilds/{READ_ONLY_GUILD}/roles/add",
        json={"user_id": "900000000000000009", "role_id": "200000000000000011"},
    )
    assert response.status_code == 403


def test_members_may_not_verify_someone_else(auth_client: TestClient) -> None:
    """Self-verification is allowed; verifying another member is not."""
    response = auth_client.post(
        f"/api/guilds/{READ_ONLY_GUILD}/verify", json={"member_id": "900000000000000042"}
    )
    assert response.status_code == 403


def test_automation_is_refused_when_the_bot_is_absent(auth_client: TestClient) -> None:
    """READ_ONLY_GUILD has no bot; even a manager could not act there."""
    enable = auth_client.patch(
        f"/api/guilds/{MANAGED_GUILD}/settings",
        json={"verification_enabled": True, "verified_role_id": "200000000000000011"},
    )
    assert enable.status_code == 200
    # Same request against the guild without the bot fails the precondition.
    response = auth_client.post(f"/api/guilds/{READ_ONLY_GUILD}/verify", json={})
    assert response.status_code == 409
