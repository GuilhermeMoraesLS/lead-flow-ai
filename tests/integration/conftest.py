from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from scripts.local import load_env

load_env()
from leadflow.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def identity():
    def signup():
        response = httpx.post(
            "http://127.0.0.1:54321/signup",
            json={
                "email": f"sl01-{uuid4().hex}@example.test",
                "password": f"Synthetic-{uuid4().hex}!",
            },
        )
        response.raise_for_status()
        body = response.json()
        return body["user"]["id"], {"Authorization": "Bearer " + body["access_token"]}

    return signup


@pytest.fixture
def identity_headers(identity):
    actor, headers = identity()
    return actor, headers
