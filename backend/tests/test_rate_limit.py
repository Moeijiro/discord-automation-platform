"""Rate limiting on the sensitive routes."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import MANAGED_GUILD


def test_verification_attempts_are_capped(auth_client: TestClient) -> None:
    """Five attempts per minute; the sixth is refused with Retry-After."""
    statuses = [
        auth_client.post(f"/api/guilds/{MANAGED_GUILD}/verify", json={}).status_code
        for _ in range(6)
    ]
    assert statuses[:5] == [409] * 5  # verification is disabled, but they count
    assert statuses[5] == 429


def test_the_limit_response_tells_the_caller_when_to_retry(
    auth_client: TestClient,
) -> None:
    for _ in range(5):
        auth_client.post(f"/api/guilds/{MANAGED_GUILD}/verify", json={})
    response = auth_client.post(f"/api/guilds/{MANAGED_GUILD}/verify", json={})
    assert response.status_code == 429
    assert int(response.headers["Retry-After"]) > 0


def test_limits_are_scoped_per_route(auth_client: TestClient) -> None:
    """Exhausting the verify window must not lock the dashboard out."""
    for _ in range(6):
        auth_client.post(f"/api/guilds/{MANAGED_GUILD}/verify", json={})
    assert auth_client.get(f"/api/guilds/{MANAGED_GUILD}").status_code == 200
