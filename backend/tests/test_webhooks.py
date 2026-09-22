"""The signed webhook endpoint."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.core.security import sign_payload
from tests.conftest import MANAGED_GUILD, UNKNOWN_GUILD

URL = "/api/webhooks/custom"
JSON_HEADERS = {"Content-Type": "application/json"}


def body_for(**overrides) -> bytes:
    payload = {
        "event": "deployment",
        "guild_id": MANAGED_GUILD,
        "message": "v1.4.0 shipped",
    }
    payload.update(overrides)
    return json.dumps(payload).encode()


def post(client: TestClient, raw: bytes, signature: str | None = None):
    headers = dict(JSON_HEADERS)
    if signature is not None:
        headers["X-Signature"] = signature
    return client.post(URL, content=raw, headers=headers)


def test_unsigned_requests_are_rejected(auth_client: TestClient) -> None:
    assert post(auth_client, body_for()).status_code == 401


def test_a_wrong_signature_is_rejected(auth_client: TestClient) -> None:
    assert post(auth_client, body_for(), "sha256=deadbeef").status_code == 401


def test_a_signature_from_a_different_body_is_rejected(auth_client: TestClient) -> None:
    """The HMAC covers the exact bytes, so a swapped body fails."""
    signature = sign_payload(body_for(message="harmless"))
    assert post(auth_client, body_for(message="tampered"), signature).status_code == 401


def test_a_signed_event_is_accepted_and_logged(auth_client: TestClient) -> None:
    raw = body_for(announce_in_channel="300000000000000013")
    response = post(auth_client, raw, sign_payload(raw))
    assert response.status_code == 202
    assert response.json()["announced"] is True

    logs = auth_client.get(f"/api/guilds/{MANAGED_GUILD}/logs").json()["items"]
    assert logs[0]["event_type"] == "webhook_received"
    assert logs[0]["message"] == "v1.4.0 shipped"
    assert logs[0]["actor_type"] == "webhook"


def test_an_unknown_guild_is_not_created_implicitly(auth_client: TestClient) -> None:
    raw = body_for(guild_id=UNKNOWN_GUILD)
    assert post(auth_client, raw, sign_payload(raw)).status_code == 404


def test_the_payload_is_validated_after_the_signature(auth_client: TestClient) -> None:
    raw = json.dumps({"event": "deployment"}).encode()  # no guild_id, no message
    assert post(auth_client, raw, sign_payload(raw)).status_code == 422


def test_unknown_event_types_are_refused(auth_client: TestClient) -> None:
    raw = body_for(event="rm -rf")
    assert post(auth_client, raw, sign_payload(raw)).status_code == 422
