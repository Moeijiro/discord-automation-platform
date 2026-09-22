"""Role automation, verification and the audit trail they write."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.services.automation import render_welcome
from tests.conftest import MANAGED_GUILD

VERIFIED_ROLE = "200000000000000011"
CONTRIBUTOR_ROLE = "200000000000000012"
MANAGED_BOT_ROLE = "200000000000000014"
MEMBER = "900000000000000042"


def enable_verification(client: TestClient) -> None:
    response = client.patch(
        f"/api/guilds/{MANAGED_GUILD}/settings",
        json={"verification_enabled": True, "verified_role_id": VERIFIED_ROLE},
    )
    assert response.status_code == 200


def test_verification_is_refused_while_disabled(auth_client: TestClient) -> None:
    response = auth_client.post(f"/api/guilds/{MANAGED_GUILD}/verify", json={})
    assert response.status_code == 409
    assert "disabled" in response.json()["detail"]


def test_verification_assigns_the_role_and_logs_both_steps(
    auth_client: TestClient,
) -> None:
    enable_verification(auth_client)
    response = auth_client.post(f"/api/guilds/{MANAGED_GUILD}/verify", json={})
    assert response.status_code == 200

    events = [
        item["event_type"]
        for item in auth_client.get(f"/api/guilds/{MANAGED_GUILD}/logs").json()["items"]
    ]
    assert "verification_completed" in events
    assert "role_added" in events


def test_verifying_twice_is_refused(auth_client: TestClient) -> None:
    enable_verification(auth_client)
    auth_client.post(f"/api/guilds/{MANAGED_GUILD}/verify", json={})
    second = auth_client.post(f"/api/guilds/{MANAGED_GUILD}/verify", json={})
    assert second.status_code == 409
    assert "already verified" in second.json()["detail"]


def test_role_add_and_remove_round_trip(auth_client: TestClient) -> None:
    body = {"user_id": MEMBER, "role_id": CONTRIBUTOR_ROLE}
    assert auth_client.post(f"/api/guilds/{MANAGED_GUILD}/roles/add", json=body).status_code == 200
    assert auth_client.post(f"/api/guilds/{MANAGED_GUILD}/roles/remove", json=body).status_code == 200

    events = [
        item["event_type"]
        for item in auth_client.get(f"/api/guilds/{MANAGED_GUILD}/logs").json()["items"]
    ]
    assert events[:2] == ["role_removed", "role_added"]


def test_integration_managed_roles_cannot_be_assigned(auth_client: TestClient) -> None:
    response = auth_client.post(
        f"/api/guilds/{MANAGED_GUILD}/roles/add",
        json={"user_id": MEMBER, "role_id": MANAGED_BOT_ROLE},
    )
    assert response.status_code == 409


def test_unknown_role_is_rejected(auth_client: TestClient) -> None:
    response = auth_client.post(
        f"/api/guilds/{MANAGED_GUILD}/roles/add",
        json={"user_id": MEMBER, "role_id": "200000000000000999"},
    )
    assert response.status_code == 404


def test_malformed_ids_never_reach_discord(auth_client: TestClient) -> None:
    response = auth_client.post(
        f"/api/guilds/{MANAGED_GUILD}/roles/add",
        json={"user_id": "me", "role_id": CONTRIBUTOR_ROLE},
    )
    assert response.status_code == 422


def test_logs_can_be_filtered_and_paged(auth_client: TestClient) -> None:
    enable_verification(auth_client)
    auth_client.post(f"/api/guilds/{MANAGED_GUILD}/verify", json={})

    page = auth_client.get(
        f"/api/guilds/{MANAGED_GUILD}/logs",
        params={"event_type": "role_added", "limit": 1},
    ).json()
    assert page["total"] == 1
    assert page["items"][0]["event_type"] == "role_added"


def test_welcome_placeholders_are_substituted() -> None:
    rendered = render_welcome(
        "Hey {user} ({username}), welcome to {server} -- member #{member_count}",
        member_id="123",
        username="ada",
        guild_name="Nebula Labs",
        member_count=7,
    )
    assert rendered == "Hey <@123> (ada), welcome to Nebula Labs -- member #7"
