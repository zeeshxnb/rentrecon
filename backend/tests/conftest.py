import json
import os
from pathlib import Path

import pytest
import httpx
from fastapi.testclient import TestClient

from app.main import app

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def test_client():
    return TestClient(app)


@pytest.fixture
def sample_post_scam():
    return (FIXTURES_DIR / "sample_post_scam.txt").read_text()


@pytest.fixture
def sample_post_legit():
    return (FIXTURES_DIR / "sample_post_legit.txt").read_text()


@pytest.fixture
def sample_zillow_response():
    return json.loads((FIXTURES_DIR / "sample_zillow_response.json").read_text())


@pytest.fixture
def sample_rentcast_response():
    return json.loads((FIXTURES_DIR / "sample_rentcast_response.json").read_text())


@pytest.fixture
def sample_realtor_response():
    return json.loads((FIXTURES_DIR / "sample_realtor_response.json").read_text())
