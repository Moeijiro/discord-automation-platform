"""Settings validation and the audit entry a change produces."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import MANAGED_GUILD

VERIFIED_ROLE = "200000000000000011"
WELCOME_CHANNEL = "300000000000000011"
SETTINGS = f"/api/guilds/{MANAGED_GUILD}/settings"


def test_defaults_are_returned_for_a_new_guild(auth_client: TestClient) -> None:
    payload = auth_client.get(SETTINGS).json()
    assert payload["verification_enabled"] is False
    assert payload["verified_role_id"] is None
    assert "{server}" in payload["welcome_message"]


def test_enabling_verification_requires_a_role(auth_client: TestClient) -> None:
    response = auth_client.patch(SETTINGS, json={"verification_enabled": True})
    assert response.status_code == 422


def test_enabling_welcome_requires_a_channel(auth_client: TestClient) -> None:
    assert auth_client.patch(SETTINGS, json={"welcome_enabled": True}).status_code == 422


def test_ids_must_look_like_snowflakes(auth_client: TestClient) -> None:
    response = auth_client.patch(SETTINGS, json={"verified_role_id": "not-an-id"})
    assert response.status_code == 422


def test_ids_must_belong_to_this_guild(auth_client: TestClient) -> None:
    """A syntactically valid ID from another server is still rejected."""
    response = auth_client.patch(
        SETTINGS,
        json={"verification_enabled": True, "verified_role_id": "200000000000000021"},
    )
    assert response.status_code == 422
    assert "does not match a role" in response.json()["detail"]


def test_unknown_fields_are_rejected(auth_client: TestClient) -> None:
    response = auth_client.patch(SETTINGS, json={"admin": True})
    assert response.status_code == 422


def test_blank_welcome_message_is_rejected(auth_client: TestClient) -> None:
    assert auth_client.patch(SETTINGS, json={"welcome_message": "   "}).status_code == 422


def test_empty_patch_is_a_bad_request(auth_client: TestClient) -> None:
    assert auth_client.patch(SETTINGS, json={}).status_code == 400


def test_valid_update_persists_and_is_audited(auth_client: TestClient) -> None:
    response = auth_client.patch(
        SETTINGS,
        json={
            "verification_enabled": True,
            "verified_role_id": VERIFIED_ROLE,
            "welcome_enabled": True,
            "welcome_channel_id": WELCOME_CHANNEL,
            "welcome_message": "Hi {user}, welcome to {server}!",
        },
    )
    assert response.status_code == 200
    assert response.json()["verified_role_id"] == VERIFIED_ROLE

    # The change survives a fresh read...
    assert auth_client.get(SETTINGS).json()["welcome_enabled"] is True

    # ...and left exactly one audit entry naming the fields that changed.
    logs = auth_client.get(f"/api/guilds/{MANAGED_GUILD}/logs").json()["items"]
    settings_logs = [item for item in logs if item["event_type"] == "settings_updated"]
    assert len(settings_logs) == 1
    assert "verified_role_id" in settings_logs[0]["event_metadata"]["changed"]
