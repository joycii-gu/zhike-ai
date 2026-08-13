"""Smoke tests for the ECS FastAPI surface using the local Skills workflow."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ["ZHIKE_ENV"] = "development"
os.environ["ZHIKE_COOKIE_SECURE"] = "false"
os.environ["ZHIKE_DATABASE_PATH"] = str(Path(tempfile.gettempdir()) / "zhike-api-test.db")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402
from backend.main import app  # noqa: E402


def run_smoke_test() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/auth/register",
            json={"email": "ecs-smoke@example.com", "display_name": "ECS 测试", "password": "safe-password-123"},
        )
        assert response.status_code in {201, 400}, response.text
        if response.status_code == 400:
            response = client.post("/api/auth/login", json={"email": "ecs-smoke@example.com", "password": "safe-password-123"})
            assert response.status_code == 200, response.text

        response = client.post(
            "/api/analysis",
            json={"customer_name": "李总", "raw_note": "李总想了解 AI 如何帮助企业培训销售团队跟进客户，希望下周线上沟通。", "force_mock": True},
        )
        assert response.status_code == 201, response.text
        customer_id = response.json()["customer_id"]
        assert customer_id

        response = client.get("/api/dashboard")
        assert response.status_code == 200, response.text
        assert response.json()["customer_count"] >= 1


if __name__ == "__main__":
    run_smoke_test()
    print("FastAPI ECS smoke test passed")
