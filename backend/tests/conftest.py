"""Test fixtures.

The environment is configured *before* the application is imported, because
settings, the engine and the gateway are resolved once at import time.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator

import pytest

TEST_DB = os.path.join(tempfile.mkdtemp(prefix="dap-tests-"), "test.db")
os.environ.update(
    ENVIRONMENT="development",
    DEMO_MODE="true",
    DATABASE_URL=f"sqlite:///{TEST_DB}",
    SESSION_SECRET="test-secret-not-used-anywhere-else",
    WEBHOOK_SECRET="test-webhook-secret",
    FRONTEND_URL="http://localhost:5173",
)

from fastapi.testclient import TestClient  # noqa: E402

from app.core.rate_limit import reset_rate_limits  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.main import app  # noqa: E402
from app.services.gateway_factory import get_gateway  # noqa: E402

MANAGED_GUILD = "100000000000000001"   # demo: owner, bot present
OTHER_GUILD = "100000000000000002"     # demo: Manage Server, bot present
READ_ONLY_GUILD = "100000000000000003" # demo: no permissions, bot absent
UNKNOWN_GUILD = "199999999999999999"


@pytest.fixture(autouse=True)
def fresh_database() -> Iterator[None]:
    """Every test starts from empty schema, gateway and rate-limit state."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    reset_rate_limits()
    get_gateway().reset()  # the demo gateway keeps in-memory role state
    yield


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app, base_url="http://localhost:8000") as test_client:
        yield test_client


@pytest.fixture
def auth_client(client: TestClient) -> TestClient:
    """A client holding a session cookie for the demo user."""
    response = client.get("/api/auth/login", follow_redirects=False)
    callback = response.headers["location"].replace("http://localhost:8000", "")
    client.get(callback, follow_redirects=False)
    assert client.get("/api/me").status_code == 200
    return client


@pytest.fixture
def db_session() -> Iterator[object]:
    with SessionLocal() as session:
        yield session
